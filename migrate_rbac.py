import sqlite3
import os

# Connect to the database (assuming backend/test.db)
DB_PATH = "backend/test.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Add 'role' column to users table
        print("Adding 'role' column to 'users' table...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'MEMBER'")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print("Column 'role' already exists.")
            else:
                print(f"Error adding column: {e}")

        # 2. Create 'invitations' table
        print("Creating 'invitations' table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invitations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR,
            token VARCHAR UNIQUE,
            organization_id INTEGER,
            role VARCHAR DEFAULT 'MEMBER',
            expires_at DATETIME,
            created_at DATETIMEDEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(organization_id) REFERENCES organizations(id)
        )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_invitations_email ON invitations (email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_invitations_token ON invitations (token)")

        conn.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
