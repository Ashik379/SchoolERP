"""
Quick fix: Add missing columns to database using direct SQL
"""
import sqlite3

# Connect to database
conn = sqlite3.connect('school.db')
cursor = conn.cursor()

try:
    # Add is_result_published to classes table
    print("Adding is_result_published column to classes table...")
    cursor.execute("ALTER TABLE classes ADD COLUMN is_result_published INTEGER DEFAULT 0")
    print("✅ Column is_result_published added successfully")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("⚠️  Column is_result_published already exists")
    else:
        print(f"❌ Error: {e}")

try:
    # Add is_result_withheld to students table
    print("\nAdding is_result_withheld column to students table...")
    cursor.execute("ALTER TABLE students ADD COLUMN is_result_withheld INTEGER DEFAULT 0")
    print("✅ Column is_result_withheld added successfully")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("⚠️  Column is_result_withheld already exists")
    else:
        print(f"❌ Error: {e}")

try:
    # Add withhold_reason to students table
    print("\nAdding withhold_reason column to students table...")
    cursor.execute("ALTER TABLE students ADD COLUMN withhold_reason TEXT")
    print("✅ Column withhold_reason added successfully")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("⚠️  Column withhold_reason already exists")
    else:
        print(f"❌ Error: {e}")

# Commit changes
conn.commit()
conn.close()

print("\n" + "="*50)
print("✅ Database migration completed successfully!")
print("="*50)
print("\nYou can now refresh the Result Manager page.")
