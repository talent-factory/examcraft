"""RabbitMQ-``consumer_timeout`` gegenüber den Celery-Zeitlimits (TF-1009).

Celery bestätigt mit ``task_acks_late=True`` erst nach Task-Ende. Bleibt eine
Nachricht länger als ``consumer_timeout`` unbestätigt, schliesst RabbitMQ den
Channel und stellt sie erneut zu, obwohl der erste Lauf noch läuft. Der
Timeout muss deshalb über dem längsten Celery-Hard-Limit liegen, in jeder
Umgebung, in der RabbitMQ läuft.

Die Tests lesen Dateien ausserhalb von ``core/backend`` und brauchen einen
Repo-Checkout (CI). Im ``core/``-Mirror fehlen ``infra/``,
``fly.rabbitmq.toml`` und ``docker-compose.full.yml``; im Compose-Container
ist nur ``core/backend`` als ``/app`` gemountet. Dort werden die betroffenen
Tests übersprungen.
"""

from __future__ import annotations

import pathlib
import re
import tomllib

import pytest
import yaml

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE_ROOT = BACKEND_ROOT.parent
REPO_ROOT = CORE_ROOT.parent
RABBITMQ_CONF = REPO_ROOT / "infra/rabbitmq/rabbitmq.conf"
FLY_RABBITMQ = REPO_ROOT / "fly.rabbitmq.toml"
COMPOSE_FULL = REPO_ROOT / "docker-compose.full.yml"
COMPOSE_CORE = CORE_ROOT / "docker-compose.yml"

CONF_GUEST_PATH = "/etc/rabbitmq/rabbitmq.conf"

# Skip-Kriterium ist fly.rabbitmq.toml, nicht die geprüfte Conf selbst: Fehlt
# die Conf im privaten Repo (z. B. umbenannt), sollen die Tests rot werden.
needs_infra = pytest.mark.skipif(
    not FLY_RABBITMQ.is_file(), reason="core/-Mirror: infra/ fehlt"
)


# Per-Task-Overrides wie ``time_limit=1800``; ``task_time_limit`` und
# ``soft_time_limit`` matchen wegen ``\b`` nicht. Statischer Scan statt
# ``celery_app.tasks``: Die Task-Module werden erst beim Worker-Start
# importiert, und premium/ lässt sich im Mirror nicht importieren. Werte, die
# keine Ganzzahl-Literale sind (Konstante, Ausdruck), lassen den Test
# scheitern statt still durchzurutschen.
TIME_LIMIT_PATTERN = re.compile(r"\btime_limit\s*=\s*([^,)\n]+?)\s*[,)\n]")
TASK_DIRS = (BACKEND_ROOT / "tasks", REPO_ROOT / "premium/backend/tasks")


def _longest_time_limit_ms() -> int:
    """Längstes Hard-Limit: global oder pro Task überschrieben."""
    from celery_app import celery_app

    limits = [celery_app.conf.task_time_limit]
    for task_dir in TASK_DIRS:
        for path in sorted(task_dir.rglob("*.py")):
            for value in TIME_LIMIT_PATTERN.findall(path.read_text(encoding="utf-8")):
                assert value.isdigit(), (
                    f"{path}: time_limit={value} ist kein Ganzzahl-Literal — "
                    "diesen Test kann es nicht auswerten, Wert als Zahl schreiben"
                )
                limits.append(int(value))
    return int(max(limits) * 1000)


def _conf_consumer_timeout_ms() -> int:
    # RabbitMQ übernimmt bei doppeltem Schlüssel den letzten Wert.
    values = re.findall(
        r"^consumer_timeout\s*=\s*(\d+)\s*$",
        RABBITMQ_CONF.read_text(encoding="utf-8"),
        re.M,
    )
    assert values, f"consumer_timeout fehlt in {RABBITMQ_CONF}"
    return int(values[-1])


@needs_infra
def test_conf_consumer_timeout_exceeds_longest_task_time_limit():
    timeout_ms = _conf_consumer_timeout_ms()
    limit_ms = _longest_time_limit_ms()

    assert timeout_ms > limit_ms, (
        f"consumer_timeout ({timeout_ms} ms) muss über dem längsten Celery-"
        f"Hard-Limit ({limit_ms} ms) liegen, sonst stellt RabbitMQ laufende "
        "acks_late-Tasks erneut zu"
    )


@needs_infra
def test_fly_rabbitmq_ships_the_conf_file():
    """Prod liest den Wert nur, wenn Fly die Datei in die Maschine legt."""
    config = tomllib.loads(FLY_RABBITMQ.read_text(encoding="utf-8"))

    files = {f["guest_path"]: f["local_path"] for f in config.get("files", [])}

    assert files.get(CONF_GUEST_PATH) == "infra/rabbitmq/rabbitmq.conf"


@needs_infra
def test_compose_full_mounts_the_conf_file():
    compose = yaml.safe_load(COMPOSE_FULL.read_text(encoding="utf-8"))

    volumes = compose["services"]["rabbitmq"]["volumes"]

    assert any(
        v.split(":")[:2] == ["./infra/rabbitmq/rabbitmq.conf", CONF_GUEST_PATH]
        for v in volumes
    ), f"docker-compose.full.yml mountet {CONF_GUEST_PATH} nicht"


@pytest.mark.skipif(
    not COMPOSE_CORE.is_file(),
    reason="Compose-Container mountet nur core/backend nach /app",
)
def test_compose_core_sets_consumer_timeout_above_task_time_limit():
    """core/ kann infra/ nicht mounten und setzt den Wert per Erlang-Argument."""
    compose = yaml.safe_load(COMPOSE_CORE.read_text(encoding="utf-8"))

    erl_args = compose["services"]["rabbitmq"]["environment"].get(
        "RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS", ""
    )
    match = re.search(r"-rabbit consumer_timeout (\d+)", erl_args)

    assert match, "core/docker-compose.yml setzt kein consumer_timeout"
    assert int(match.group(1)) > _longest_time_limit_ms()
    if RABBITMQ_CONF.is_file():
        assert int(match.group(1)) == _conf_consumer_timeout_ms(), (
            "core/docker-compose.yml und infra/rabbitmq/rabbitmq.conf "
            "weichen voneinander ab"
        )


def test_worker_cancels_acks_late_tasks_on_connection_loss():
    """Nach einem Verbindungsabbruch kann ein acks_late-Task nicht mehr
    bestätigen, die Nachricht kommt erneut. Liefe der erste Lauf weiter,
    würden die Idempotenz-Guards der Portfolio-Tasks einen lebenden Lauf als
    failed markieren."""
    from celery_app import celery_app

    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_cancel_long_running_tasks_on_connection_loss is True
