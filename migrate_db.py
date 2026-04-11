import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'database', 'instance', 'fload.db')
if not os.path.exists(db_path):
    print("Database not found. It will be created on next startup.")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check for college_id in students
cursor.execute("PRAGMA table_info(students)")
columns = [col[1] for col in cursor.fetchall()]

if 'college_id' not in columns:
    print("Adding college_id to students table...")
    cursor.execute("ALTER TABLE students ADD COLUMN college_id INTEGER")

# Check for college_id in majors
cursor.execute("PRAGMA table_info(majors)")
columns = [col[1] for col in cursor.fetchall()]

if 'college_id' not in columns:
    print("Adding college_id to majors table...")
    cursor.execute("ALTER TABLE majors ADD COLUMN college_id INTEGER")

# Create colleges table if missing
cursor.execute("""
CREATE TABLE IF NOT EXISTS colleges (
    college_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL
)
""")

conn.commit()
conn.close()
print("Migration completed successfully.")
