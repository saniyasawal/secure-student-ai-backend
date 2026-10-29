
import json
import random
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

students = []

for i in range(1, 101):
    student_id = f"S{1000 + i}"

    student = {
        "student_id": student_id,
        "name": f"Student {i:03d}",
        "marks": {
            "Python": random.randint(35, 100),
            "Machine Learning": random.randint(35, 100),
            "Cloud Computing": random.randint(35, 100)
        },
        "attendance": random.randint(55, 100)
    }

    students.append(student)

output_file = DATA_DIR / "students.json"

with output_file.open("w", encoding="utf-8") as file:
    json.dump(students, file, indent=2)

print(f"Successfully generated {len(students)} synthetic student records.")
print(f"Saved to: {output_file}")
print(f"First student ID: {students[0]['student_id']}")
print(f"Last student ID: {students[-1]['student_id']}")
