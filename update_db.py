import sqlite3

# Database file ka naam check kar lena (school.db ya school_erp.db)
db_name = "school.db" 

try:
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # 4 Naye Columns add karne ki commands
    columns = [
        "ALTER TABLE students ADD COLUMN apaar_id VARCHAR",
        "ALTER TABLE students ADD COLUMN pan_no VARCHAR",
        "ALTER TABLE students ADD COLUMN father_aadhaar VARCHAR",
        "ALTER TABLE students ADD COLUMN mother_aadhaar VARCHAR"
    ]

    for col in columns:
        try:
            cursor.execute(col)
            print(f"Success: {col}")
        except sqlite3.OperationalError as e:
            print(f"Skipped (shyad pehle se hai): {e}")

    conn.commit()
    conn.close()
    print("\n✅ Database Updated Successfully! Ab server restart karein.")

except Exception as e:
    print(f"❌ Error: {e}")