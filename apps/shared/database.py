"""
Database engine, session factory, and FastAPI dependency.

WHY THIS FILE EXISTS
--------------------
Both the API and the Worker need to talk to Postgres.  This module creates
a single SQLAlchemy *engine* (the connection pool) and a *SessionLocal*
factory (produces one session per request / per task).

KEY CONCEPTS
------------
- Engine:       manages LOW-LEVEL database connections (connection pool).
- SessionLocal: a factory that creates Session objects. Each Session is a
                "unit of work" — you open it, do reads/writes, then close it.
- get_db():     a FastAPI *dependency* that yields a session.  FastAPI calls
                it automatically for every request that declares it as a
                parameter, and closes the session when the request finishes.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


def _database_url() -> str:
    """Read DATABASE_URL from the environment (set in docker-compose)."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://legal:legal@localhost:5432/legal_rag",
    )


engine = create_engine(_database_url(), echo=False)

# SessionLocal is NOT a session — it is a *factory* that creates sessions.
# Call  session = SessionLocal()  to get an actual session.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """
    FastAPI dependency that provides a database session.

    Usage in a route:
        @router.post("/something")
        def do_something(db: Session = Depends(get_db)):
            ...

    The `yield` makes this a *generator dependency*.  FastAPI will:
      1. Call next() to get the session (before your route runs).
      2. Give it to your route via the `db` parameter.
      3. After your route returns (or raises), execute the `finally` block.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
