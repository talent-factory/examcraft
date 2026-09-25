from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import database models for autogenerate support
from database import Base, _normalize_db_url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with DATABASE_URL environment variable if present.
# Normalized the same way as the main engine (TF-424 legacy scheme rewrite,
# TF-938 explicit psycopg2 driver) since this reads DATABASE_URL directly,
# bypassing database.py's own normalization of its module-level DATABASE_URL.
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", _normalize_db_url(database_url))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# disable_existing_loggers=False: database._run_migrations_or_create_all()
# runs stamp/upgrade inside the API process; the default would silence every
# router and service logger created before startup for the process lifetime.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# add your model's MetaData object here
# for 'autogenerate' support
from models.question_generation_job import QuestionGenerationJob  # noqa: F401, E402

# Import premium models for Full deployment mode
try:
    from premium.models.chat_db import ChatSession, ChatMessage  # noqa: F401
    from premium.models.prompt import Prompt, PromptTemplate, PromptUsageLog  # noqa: F401
    from premium.models.wizard import WizardSession, WizardMessage  # noqa: F401
except ImportError:
    pass  # Core mode - premium models not available

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
