import sqlite3

conn = sqlite3.connect('school.db')
cursor = conn.cursor()

print("--- UPDATING EXAM SCHEDULE TABLE ---")

try:
    cursor.execute("ALTER TABLE exam_schedule ADD COLUMN max_marks INTEGER DEFAULT 100")
    print("✅ Added 'max_marks'")
except:
    print("ℹ️ 'max_marks' already exists")

try:
    cursor.execute("ALTER TABLE exam_schedule ADD COLUMN pass_marks INTEGER DEFAULT 33")
    print("✅ Added 'pass_marks'")
except:
    print("ℹ️ 'pass_marks' already exists")

conn.commit()
conn.close()
print("\n--- DONE! Server Restart Zaroori Hai ---")