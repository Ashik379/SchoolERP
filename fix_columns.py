import sqlite3

# Database se connect karein
conn = sqlite3.connect('school.db')
cursor = conn.cursor()

# List of columns to add (Column Name, Data Type)
columns_to_add = [
    ("dob", "DATE"),
    ("religion", "VARCHAR(50)"),
    ("caste", "VARCHAR(50)"),
    ("category", "VARCHAR(20)"),
    ("aadhaar_no", "VARCHAR(20)"),
    ("blood_group", "VARCHAR(5)"),
    ("father_occupation", "VARCHAR(100)"),
    ("mother_occupation", "VARCHAR(100)"),
    ("father_mobile", "VARCHAR(15)"),
    ("address", "VARCHAR(255)"),
    ("city", "VARCHAR(100)"),
    ("previous_school", "VARCHAR(200)"),
    ("transport_opted", "BOOLEAN DEFAULT 0"),
    ("pickup_point_id", "INTEGER"),
    ("student_photo", "VARCHAR(255)"),
    ("current_balance", "FLOAT DEFAULT 0.0")
]

print("🛠 Checking and Fixing Database Columns...")

for col_name, col_type in columns_to_add:
    try:
        # SQL query to add column
        cursor.execute(f"ALTER TABLE students ADD COLUMN {col_name} {col_type}")
        print(f"✅ Added column: {col_name}")
    except sqlite3.OperationalError as e:
        # Agar column pehle se hai, toh ye error aayega (Ignore karein)
        if "duplicate column" in str(e):
            print(f"ℹ️ Column '{col_name}' already exists.")
        else:
            print(f"⚠️ Could not add '{col_name}': {e}")

conn.commit()
conn.close()

print("\n🎉 Database repair finished! Now restart your server.")