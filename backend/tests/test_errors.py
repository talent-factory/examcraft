"""Direkte Unit-Tests für ``core/backend/errors.py`` (TF-773 review).

``test_error_codes_contract.py`` prüft die Codes statisch über den ganzen
Baum, ``test_error_envelope.py`` prüft das Envelope über HTTP. Beides trifft
nie die eigentlichen Guards in ``errors.py`` selbst direkt — hier die vier
Invarianten, isoliert von jeder Route und jeder DB.
"""

from __future__ import annotations

import pytest

from errors import RESERVED_ERROR_CODES, AppHTTPException, api_error


class TestReservedErrorCodes:
    """``validation_error``/``internal_error`` gehören den Framework-Handlern
    in main.py — ein hand-geschriebener Aufruf darf sie nicht kapern."""

    def test_api_error_lehnt_reservierten_code_ab(self):
        with pytest.raises(ValueError, match="reserved"):
            api_error(500, "internal_error", "de")

    def test_app_http_exception_lehnt_reservierten_code_ab(self):
        with pytest.raises(ValueError, match="reserved"):
            AppHTTPException(422, "x", error_code="validation_error")

    def test_alle_reservierten_codes_werden_abgelehnt(self):
        for code in RESERVED_ERROR_CODES:
            with pytest.raises(ValueError):
                AppHTTPException(500, "x", error_code=code)


class TestDetailMussString:
    """Die 89 Frontend-Stellen lesen ``detail`` als String — ein Dict/eine
    Liste hier würde genau die TF-671-Regression lautlos reproduzieren."""

    def test_dict_detail_wird_abgelehnt(self):
        with pytest.raises(TypeError, match="str"):
            AppHTTPException(402, {"error_code": "x"}, error_code="foo")

    def test_string_detail_ist_ok(self):
        exc = AppHTTPException(404, "Nicht gefunden", error_code="foo_not_found")
        assert exc.detail == "Nicht gefunden"
        assert exc.error_code == "foo_not_found"
        assert exc.error_params is None


class TestPositionalOnlyKollisionen:
    """``status_code``/``code``/``locale``/``headers`` sind positional-only,
    damit eine Interpolationsvariable so heissen darf, ohne mit api_error()s
    eigener Signatur zu kollidieren."""

    def test_code_als_interpolationsname_kollidiert_nicht(self):
        exc = api_error(409, "test_dummy_code", "de", code="K1")
        assert exc.error_params == {"code": "K1"}

    def test_status_code_als_interpolationsname_kollidiert_nicht(self):
        exc = api_error(409, "test_dummy_code", "de", status_code=999)
        assert exc.error_params == {"status_code": 999}

    def test_echte_headers_funktionieren_weiterhin_positional(self):
        exc = api_error(401, "test_dummy_code", "de", {"WWW-Authenticate": "Bearer"})
        assert exc.headers == {"WWW-Authenticate": "Bearer"}
        assert exc.error_params is None

    def test_headers_als_interpolationsname_landet_nicht_mehr_in_echten_headern(self):
        """Vor dieser Änderung (TF-773 review) war ``headers`` nur
        keyword-only: eine als Interpolationswert gemeinte ``headers=``-
        Angabe landete still im echten HTTP-Headers-Parameter statt in
        ``error_params`` — der gerenderte Text zeigte das rohe
        ``%{headers}``-Platzhalter, und die Response trug einen unsinnigen
        Header-Wert, ohne dass irgendetwas fehlschlug. Jetzt ist ``headers``
        wie die anderen drei positional-only, also fällt eine
        Keyword-Angabe in ``**params``."""
        exc = api_error(403, "test_dummy_code", "de", headers="not-a-real-header")
        assert exc.headers is None
        assert exc.error_params == {"headers": "not-a-real-header"}


class TestReservierteInterpolationsnamen:
    """``key``/``locale`` sind ``t()``s eigene benannte Parameter — die kann
    dieses Modul nicht positional-only machen, ohne ~265 bestehende
    Aufrufstellen von ``t()`` selbst zu brechen. Stattdessen ein früher,
    klarer ``TypeError`` statt eines kryptischen Fehlers tief in ``t()``."""

    def test_locale_als_interpolationsname_wird_abgelehnt(self):
        with pytest.raises(TypeError, match="locale"):
            api_error(400, "test_dummy_code", "de", locale="fr")

    def test_key_als_interpolationsname_wird_abgelehnt(self):
        with pytest.raises(TypeError, match="key"):
            api_error(400, "test_dummy_code", "de", key="whatever")
