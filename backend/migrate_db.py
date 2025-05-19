import os
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def recreate_database(db_path):
    """Recreate the database from scratch if migration fails"""
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Deleted existing database: {db_path}")

        from backend.classifier import MilkMobClassifier

        MilkMobClassifier(db_path=db_path)
        logger.info(f"Created new database: {db_path}")
    except Exception as e:
        logger.error(f"Failed to recreate database: {e}")


def table_exists(cursor, table):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cursor.fetchone() is not None

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(col[1] == column for col in cursor.fetchall())

def add_column(cursor, table, column_def):
    logger.info(f"Adding column {column_def} to {table}")
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")

def migrate(db_path="milk_mobs.db"):
    """Upgrade the SQLite database schema if needed."""
    try:
        if not os.path.exists(db_path):
            logger.warning(f"Database {db_path} not found. Creating new database.")
            recreate_database(db_path)
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        required_tables = ["mobs", "videos", "mob_keywords"]
        missing_tables = [t for t in required_tables if not table_exists(cursor, t)]

        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}. Recreating database.")
            conn.close()
            recreate_database(db_path)
            return

        # Mobs table upgrades
        if not column_exists(cursor, "mobs", "color_theme"):
            add_column(cursor, "mobs", "color_theme TEXT")
        if not column_exists(cursor, "mobs", "icon"):
            add_column(cursor, "mobs", "icon TEXT")

        # Videos table upgrades
        if not column_exists(cursor, "videos", "description"):
            add_column(cursor, "videos", "description TEXT")
        if not column_exists(cursor, "videos", "thumbnail_path"):
            add_column(cursor, "videos", "thumbnail_path TEXT")
        if not column_exists(cursor, "videos", "video_path"):
            add_column(cursor, "videos", "video_path TEXT")

        conn.commit()
        logger.info("Database migration completed")
    except Exception as e:
        logger.error(f"Migration error: {e}")
        recreate_database(db_path)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate()
