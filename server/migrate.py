import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "trends.db")

def add_column_if_missing(cursor, table, column, col_type):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    if column not in columns:
        print(f"➕ Adding column: {column}")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    else:
        print(f"✅ Column already exists: {column}")

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("🔄 Migrating schema...")
    add_column_if_missing(cursor, "trends", "stage", "TEXT")
    add_column_if_missing(cursor, "trends", "examples", "TEXT")
    add_column_if_missing(cursor, "trends", "url", "TEXT")

    conn.commit()
    conn.close()
    print("✅ Migration complete.")

if __name__ == "__main__":
    migrate()

