import sqlite3

conn = sqlite3.connect('school.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE students ADD COLUMN roll_no INTEGER")
    print("✅ Success: 'roll_no' column added!")
except Exception as e:
    print(f"ℹ️ Info: {e}")

conn.commit()
conn.close()