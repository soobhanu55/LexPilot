import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# GDPR Note: All data is stored locally in this PostgreSQL database.
# No third-party APIs are called with user data, ensuring 100% data 
# residency and GDPR compliance for enterprise deployments.

pool = None

def init_pool():
    global pool
    if pool is None:
        try:
            pool = ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                host=settings.postgres_host,
                port=settings.postgres_port,
                dbname=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            # Do not crash, as this file might be imported before PG is up
            
init_pool()

@contextmanager
def get_conn():
    global pool
    if pool is None:
        init_pool()
        if pool is None:
            raise Exception("Database connection pool not initialized.")
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)

def initialize_database():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Check if tables exist
                cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'companies');"
                )
                exists = cur.fetchone()[0]
                if not exists:
                    logger.info("Initializing database schema...")
                    migration_path = os.path.join(os.path.dirname(__file__), "migrations", "001_init.sql")
                    with open(migration_path, "r", encoding="utf-8") as f:
                        cur.execute(f.read())
                    logger.info("Schema generated.")
    except Exception as e:
        logger.warning(f"Could not initialize database on import: {e}")

# Run init on module load
initialize_database()
