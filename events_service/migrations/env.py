import os
import sys
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

version_table = "alembic_version_events"
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our models and configuration
try:
    from app.models.event import Base
    logger.info("Successfully imported event models")
except Exception as e:
    logger.error(f"Failed to import models: {e}")
    raise

try:
    from app.core.config import config
    logger.info("Successfully imported config")
except Exception as e:
    logger.error(f"Failed to import config: {e}")
    raise

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
alembic_config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata
logger.info("Target metadata set successfully")

# Configure Alembic to only manage events tables
def include_object(object, name, type_, reflected, compare_to):
    """Filter objects to only include events tables."""
    if type_ == "table":
        # Only include tables that are defined in our event models
        # Get table names from our Base metadata
        events_table_names = set(target_metadata.tables.keys())
        return name in events_table_names
    return True

def get_database_url():
    """Get database URL from app.core.config."""
    import asyncio
    
    logger.info("Getting database URL from config...")
    
    async def _get_url():
        logger.info("Calling config.get_database_url()...")
        url = await config.get_database_url()
        logger.info(f"Database URL retrieved successfully: {url[:50]}...")
        return url
    
    try:
        url = asyncio.run(_get_url())
        logger.info("Database URL retrieved successfully")
        return url
    except Exception as e:
        logger.error(f"Failed to get database URL from config: {e}")
        raise EnvironmentError(f"Failed to get database URL from config: {e}")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    logger.info("Running migrations in offline mode...")
    url = get_database_url()
    logger.info(f"Using database URL: {url[:50]}...")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        logger.info("Running migrations...")
        context.run_migrations()
        logger.info("Migrations completed successfully")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    logger.info("Running migrations in online mode...")
    database_url = get_database_url()
    logger.info(f"Using database URL: {database_url[:50]}...")
    
    # Create engine directly with the database URL
    logger.info("Creating database engine...")
    connectable = engine_from_config(
        {"sqlalchemy.url": database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        logger.info("Connected to database successfully")
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_object=include_object,
            version_table=version_table,
        )

        with context.begin_transaction():
            logger.info("Running migrations...")
            context.run_migrations()
            logger.info("Migrations completed successfully")


if context.is_offline_mode():
    logger.info("Running in offline mode")
    run_migrations_offline()
else:
    logger.info("Running in online mode")
    run_migrations_online()