from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from urllib.parse import quote_plus
from pathlib import Path

from app.core.config import (
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
)

encoded_password = quote_plus(DB_PASSWORD)

BASE_DIR = Path(__file__).resolve().parent

RENDER_CA_PATH = Path("/etc/secrets/ca.pem")
LOCAL_CA_PATH = BASE_DIR / "certs" / "ca.pem"

CA_CERT_PATH = RENDER_CA_PATH if RENDER_CA_PATH.exists() else LOCAL_CA_PATH

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{encoded_password}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={
        "ssl_ca": str(CA_CERT_PATH),
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
    },
)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()