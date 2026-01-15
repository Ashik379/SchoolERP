import sqlite3

conn = sqlite3.connect('school.db')
cursor = conn.cursor()

print("=== CLASSES TABLE SCHEMA ===")
cursor.execute("PRAGMA table_info(classes)")
for row in cursor.fetchall():
    print(f"{row[1]}: {row[2]}")

print("\n=== STUDENTS TABLE SCHEMA (relevant columns) ===")
cursor.execute("PRAGMA table_info(students)")
all_cols = cursor.fetchall()
for row in all_cols:
    if 'result' in row[1].lower() or 'withhold' in row[1].lower():
        print(f"{row[1]}: {row[2]}")

conn.close()
