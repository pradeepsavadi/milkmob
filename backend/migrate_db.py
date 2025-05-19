import os
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(col[1] == column for col in cursor.fetchall())

def add_column(cursor, table, column_def):
    logger.info(f"Adding column {column_def} to {table}")
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")

def migrate(db_path="milk_mobs.db"):
    """Upgrade the SQLite database schema if needed."""
    if not os.path.exists(db_path):
        logger.warning(f"Database {db_path} not found. No migration needed.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
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
        logger.error(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
