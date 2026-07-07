import logging

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import ASYNC_DATABASE_URL

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _add_missing_columns_sync(conn) -> None:
    """Compare model definitions with existing tables and add any missing columns."""
    from . import models  # noqa: F401

    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue

        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        model_columns = {col.name for col in table.columns}

        for col_name in model_columns - existing_columns:
            col = table.c[col_name]
            col_type = col.type.compile(dialect=conn.dialect)
            nullable = "NULL" if col.nullable else "NOT NULL"
            default = ""
            if col.server_default is not None:
                default_val = col.server_default.arg
                if callable(default_val):
                    default_val = default_val()
                default = f" DEFAULT {default_val}"
            elif col.default is not None:
                default = f" DEFAULT {col.default.arg}"

            sql = f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {nullable}{default}'
            logger.info("Adding missing column: %s", sql)
            conn.execute(text(sql))


async def init_db() -> None:
    """Create missing tables and add missing columns from SQLAlchemy models."""
    from . import models  # noqa: F401 (ensure models are registered)

    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns_sync)
    logger.info("Database schema initialization complete.")
