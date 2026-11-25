import socket
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# In-memory DNS cache to avoid repeated DNS resolution latency and ISP blocks
_dns_cache = {
    "ep-billowing-feather-bec9s4pv-pooler.c-9.us-east-2.aws.neon.tech": "3.147.219.177",
    "ep-billowing-feather-bec9s4pv.c-9.us-east-2.aws.neon.tech": "3.147.219.177",
    "ep-super-shape-biou41ba-pooler.c-5.ap-southeast-1.aws.neon.tech": "47.131.202.219",
    "ep-super-shape-biou41ba.c-5.ap-southeast-1.aws.neon.tech": "47.131.202.219",
}
_system_getaddrinfo = socket.getaddrinfo


def _fallback_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if isinstance(host, str) and host in _dns_cache:
        return _system_getaddrinfo(_dns_cache[host], port, family, type, proto, flags)
    try:
        return _system_getaddrinfo(host, port, family, type, proto, flags)
    except socket.gaierror:
        if isinstance(host, str) and "neon.tech" in host:
            try:
                import dns.resolver
                resolver = dns.resolver.Resolver()
                resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
                answers = resolver.resolve(host, "A")
                if answers:
                    ip = str(answers[0].address)
                    _dns_cache[host] = ip
                    return _system_getaddrinfo(ip, port, family, type, proto, flags)
            except Exception:
                pass
        raise


socket.getaddrinfo = _fallback_getaddrinfo

# Connection arguments optimized for Neon PgBouncer transaction pooling
connect_args = {
    "prepared_statement_cache_size": 0,
    "statement_cache_size": 0,
}


def _normalize_database_url(url: str) -> str:
    """Normalize database connection URL to ensure asyncpg driver and clean SSL options."""
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "sslmode=require" in url:
        url = url.replace("sslmode=require", "ssl=require")
    elif "sslmode=verify-full" in url:
        url = url.replace("sslmode=verify-full", "ssl=require")
    return url


# Create async database engine with connection pooling optimized for Neon pooler
engine = create_async_engine(
    _normalize_database_url(settings.DATABASE_URL),
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args=connect_args
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Base class for SQLAlchemy declarative models
Base = declarative_base()


# Dependency to yield database sessions per request
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
