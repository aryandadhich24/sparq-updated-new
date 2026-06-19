import sqlite3
import os

# Connect to the database (assuming backend/test.db)
DB_PATH = "backend/test.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. Skipping migration (tables will be created fresh).")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(organizations)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "settings" not in columns:
            print("Adding 'settings' column to 'organizations' table...")
            cursor.execute("ALTER TABLE organizations ADD COLUMN settings JSON DEFAULT '{}'")
            conn.commit()
            print("Migration successful.")
        else:
            print("'settings' column already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
