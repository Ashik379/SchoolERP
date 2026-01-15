import sqlite3

# Database se connect karo
conn = sqlite3.connect('school.db')
cursor = conn.cursor()

print("--- FIXING DATABASE FOR FETCHING ---")

try:
    # Subjects table mein 'subject_type' column jodo (Jo missing hai)
    cursor.execute("ALTER TABLE subjects ADD COLUMN subject_type VARCHAR(20) DEFAULT 'Theory'")
    print("✅ Fixed: 'subject_type' column added.")
except Exception as e:
    print(f"ℹ️ Info: {e}")

try:
    # Subjects table mein 'subject_code' column jodo
    cursor.execute("ALTER TABLE subjects ADD COLUMN subject_code VARCHAR(20)")
    print("✅ Fixed: 'subject_code' column added.")
except Exception as e:
    pass

conn.commit()
conn.close()
print("\n--- DONE! Ab Server Restart karke check karo ---")