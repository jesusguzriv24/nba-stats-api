import os
import ssl
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONSOLE LOGGING START ---
print("\n" + "="*60)
print(" >> INITIALIZING DATABASE CONNECTION")
print("-" * 60)

# 1. Retrieve original URL
database_url = os.getenv("DATABASE_URL")

if not database_url:
    print(" [!] ERROR: DATABASE_URL not found in environment variables.")
    print("="*60 + "\n")
    raise ValueError("DATABASE_URL is missing")

# 2. Clean the URL: remove '?sslmode=require' parameter if present
# asyncpg fails if it sees "sslmode" in the URL
if "?sslmode=" in database_url:
    print(" [-] Cleaning URL parameters (removing sslmode)...")
    database_url = database_url.split("?sslmode=")[0]

# 3. Replace scheme for asyncpg
print(" [-] Updating protocol to postgresql+asyncpg...")
database_url = database_url.replace("postgres://", "postgresql+asyncpg://")

# Decide if SSL should be used (remote) or not (local/docker)
parsed = urlparse(database_url)
host = parsed.hostname or ""

use_ssl = host not in ("db", "localhost", "127.0.0.1")

connect_args = {}

if use_ssl:
    print(" [-] Creating secure SSL context (remote DB)...")
    ssl_context = ssl.create_default_context()
    # Opcionales, según tu caso remoto:
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context
else:
    print(" [-] Local/Docker DB detected, SSL disabled.")

# 5. Configure the engine
print(" [-] Creating async engine...")
engine = create_async_engine(
    database_url,
    echo=False,  # Set to False in production to reduce noise
    connect_args=connect_args,
    poolclass=NullPool,  # Disable pooling for serverless; puedes cambiar si quieres
)

print(" >> DATABASE CONFIGURATION COMPLETE")
print("="*60 + "\n")

# Create the session factory (Session Local)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

# Base class for models (Tables)
class Base(DeclarativeBase):
    pass

# Dependency to get DB session in FastAPI endpoints
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
