"""
Módulo de conexión asíncrona a la base de datos con SQLAlchemy 2.0 y asyncpg.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config.settings import settings
from app.database.models import Base
from app.logger.logger import sys_logger


# Detectar si se requiere SSL (ej. Supabase, Heroku, Neon, AWS)
extra_connect_args = {}
if "supabase" in settings.DATABASE_URL.lower() or "ssl=require" in settings.DATABASE_URL.lower() or "pooler.supabase.com" in settings.DATABASE_URL.lower():
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    extra_connect_args["ssl"] = ssl_context

# Crear engine asíncrono
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=extra_connect_args,
)

# Factory de sesiones asíncronas
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db(override_engine=None) -> None:
    """
    Inicializa las tablas en la base de datos de manera asíncrona.
    """
    target_engine = override_engine or engine
    try:
        async with target_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sys_logger.info("Base de datos: Tablas creadas/verificadas correctamente.")
    except Exception as e:
        sys_logger.error(f"Error al inicializar la base de datos: {e}")


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency generator para obtener sesiones asíncronas de base de datos.
    """
    async with async_session_factory() as session:
        yield session
