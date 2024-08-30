from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings

SQLALCHEMY_DATABASE_URL = settings.sqlalchemy_database_url
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()