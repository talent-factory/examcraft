"""
Profile picture handling for ExamCraft AI (EXAMCRAFT-168).

Syncs the IdP picture into ``users`` at login (SSRF-hardened download),
normalises uploads, and stores the result in the user row.
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stored profile picture (EXAMCRAFT-168)
# ---------------------------------------------------------------------------

AVATAR_MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # raw upload limit
AVATAR_MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024  # IdP picture limit
AVATAR_MAX_PIXELS = 25_000_000  # checked before decoding (bomb guard)
AVATAR_SIZE = 256  # stored edge length in px
AVATAR_SOURCE_IDP = "idp"
AVATAR_SOURCE_UPLOAD = "upload"


class InvalidAvatarImage(ValueError):
    """The bytes are not a usable image."""


def normalize_avatar_image(raw: bytes) -> bytes:
    """Decode, centre-crop to a square, resize and re-encode as PNG.

    Re-encoding drops EXIF/GPS metadata and anything that is not pixel data.
    Raises ``InvalidAvatarImage`` for non-images, unsupported formats, images
    above ``AVATAR_MAX_PIXELS`` and truncated files. Animated files keep their
    first frame.
    """
    from io import BytesIO

    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with Image.open(BytesIO(raw), formats=("PNG", "JPEG", "WEBP", "GIF")) as img:
            # Explicit limit before decoding: Pillow's own guard only raises at
            # twice MAX_IMAGE_PIXELS, a small PNG could still need ~200 MB.
            if img.width * img.height > AVATAR_MAX_PIXELS:
                raise InvalidAvatarImage("image has too many pixels")
            img.load()
            img = ImageOps.exif_transpose(img)
            img = ImageOps.fit(
                img.convert("RGBA"), (AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS
            )
            out = BytesIO()
            img.save(out, format="PNG", optimize=True)
            return out.getvalue()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        ValueError,
        SyntaxError,
    ) as exc:
        raise InvalidAvatarImage(str(exc)) from exc


def store_avatar(user, raw: bytes, source: str) -> None:
    """Normalise ``raw`` and set the avatar columns on ``user`` (no commit)."""
    from datetime import datetime, timezone

    user.avatar_data = normalize_avatar_image(raw)
    user.avatar_content_type = "image/png"
    user.avatar_source = source
    user.avatar_updated_at = datetime.now(timezone.utc)


def clear_avatar(user) -> None:
    """Remove the stored picture (no commit)."""
    user.avatar_data = None
    user.avatar_content_type = None
    user.avatar_source = None
    user.avatar_updated_at = None


# Hosts the IdP picture may be fetched from (exact match or dotted suffix).
# The OIDC issuer host is always allowed; more hosts via AVATAR_ALLOWED_HOSTS
# (comma separated).
_DEFAULT_AVATAR_HOSTS = ("googleusercontent.com",)


def _normalize_host(host: Optional[str]) -> str:
    return (host or "").rstrip(".").lower()


def _allowed_avatar_hosts() -> list[str]:
    import os
    from urllib.parse import urlparse

    hosts = [_normalize_host(h) for h in _DEFAULT_AVATAR_HOSTS]
    hosts += [
        _normalize_host(h)
        for h in os.getenv("AVATAR_ALLOWED_HOSTS", "").split(",")
        if h.strip()
    ]
    issuer = os.getenv("OIDC_ISSUER", "")
    if issuer:
        hosts.append(_normalize_host(urlparse(issuer).hostname))
    return [h for h in hosts if h]


def _host_allowed(host: str) -> bool:
    return any(host == h or host.endswith("." + h) for h in _allowed_avatar_hosts())


def _resolve_public_ip(host: str, port: int) -> Optional[str]:
    """Resolve ``host`` and return one address, or None if ANY address is not public.

    Loopback, private, link-local, reserved, multicast and unspecified targets
    are refused. The caller connects to the returned IP, so a second DNS
    lookup (rebinding) cannot change the target.
    """
    import ipaddress
    import socket

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        logger.warning("Avatar-Sync: Host nicht auflösbar (host=%s).", host)
        return None
    addresses = []
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0].split("%")[0])
        except ValueError:
            return None
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
            or not ip.is_global
        ):
            logger.warning("Avatar-Sync: Ziel nicht öffentlich (host=%s).", host)
            return None
        addresses.append(ip)
    if not addresses:
        return None
    return str(addresses[0])


def _fetch_idp_picture(url: str) -> Optional[bytes]:
    """Download the IdP picture (SSRF-hardened).

    https only, host on the allowlist, every resolved address public, the
    connection pinned to the checked IP (TLS still verifies the hostname via
    SNI), no redirects, size-capped.
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        port = parsed.port or 443
    except ValueError:
        logger.warning("Avatar-Sync: URL nicht auswertbar.")
        return None
    host = _normalize_host(parsed.hostname)
    if parsed.scheme.lower() != "https" or not host:
        logger.warning("Avatar-Sync: Nicht-https-URL ignoriert.")
        return None
    if parsed.username or parsed.password:
        logger.warning("Avatar-Sync: URL mit Zugangsdaten abgelehnt (host=%s).", host)
        return None
    if not _host_allowed(host):
        logger.warning("Avatar-Sync: Host nicht erlaubt (host=%s).", host)
        return None
    ip = _resolve_public_ip(host, port)
    if ip is None:
        return None
    ip_host = f"[{ip}]" if ":" in ip else ip
    netloc = ip_host if port == 443 else f"{ip_host}:{port}"
    pinned_url = parsed._replace(netloc=netloc).geturl()
    request_headers = {"Host": host if port == 443 else f"{host}:{port}"}
    request_extensions = {"sni_hostname": host}
    try:
        with httpx.Client(timeout=5, follow_redirects=False) as client:
            with client.stream(
                "GET",
                pinned_url,
                headers=request_headers,
                extensions=request_extensions,
            ) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    logger.warning(
                        "Avatar-Sync: kein Bild (host=%s, content-type=%s).",
                        host,
                        content_type,
                    )
                    return None
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > AVATAR_MAX_DOWNLOAD_BYTES:
                        logger.warning("Avatar-Sync: Bild zu gross.")
                        return None
                return bytes(data)
    except httpx.HTTPError as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning(
            "Avatar-Sync: Download fehlgeschlagen (%s, status=%s).",
            type(exc).__name__,
            status_code,
        )
        return None


def sync_idp_avatar(db, user, picture_url: Optional[str]) -> bool:
    """Copy the IdP picture into the user row at login. Never raises.

    Skipped when the user uploaded their own picture, when the claim is
    empty, or when the same URL was already synced. Returns True if the
    stored picture changed.
    """
    try:
        if user.avatar_source == AVATAR_SOURCE_UPLOAD or not picture_url:
            return False
        if picture_url == user.avatar_url and user.avatar_data is not None:
            return False
        raw = _fetch_idp_picture(picture_url)
        if raw is None:
            return False
        store_avatar(user, raw, AVATAR_SOURCE_IDP)
        user.avatar_url = picture_url
        db.commit()
        return True
    except InvalidAvatarImage:
        db.rollback()
        logger.warning("Avatar-Sync: IdP-Bild nicht verwendbar (user_id=%s).", user.id)
        return False
    except Exception:
        db.rollback()
        logger.exception("Avatar-Sync fehlgeschlagen (user_id=%s).", user.id)
        return False
