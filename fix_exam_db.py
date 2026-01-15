import sqlite3

# Database se connect karo
conn = sqlite3.connect('school.db')
cursor = conn.cursor()

print("--- FIXING EXAM DATABASE ---")

try:
    # 1. Exam Types table mein 'session' column jodo
    cursor.execute("ALTER TABLE exam_types ADD COLUMN session VARCHAR(20) DEFAULT '2025-26'")
    print("✅ Fixed: 'session' column added to 'exam_types'.")
except Exception as e:
    print(f"ℹ️ Info: {e} (Shayad pehle se hai)")

conn.commit()
conn.close()
print("\n--- DONE! Ab Server Restart karein ---")