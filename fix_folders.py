import os

# 1. Folders Banayein
paths = [
    "static",
    "static/uploads",
    "static/uploads/students",
    "static/images"
]

print("--- CHECKING FOLDERS ---")
for p in paths:
    if not os.path.exists(p):
        os.makedirs(p)
        print(f"✅ Created: {p}")
    else:
        print(f"🔹 Exists: {p}")

print("\n--- DONE ---")
print("Ab Server Restart karein aur Student Add karein.")