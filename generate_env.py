
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
env_file = BASE_DIR / ".env"

lines = [
    "API_KEY=local-demo-key-2026"
]

for i in range(1, 101):
    student_id = f"S{1000 + i}"
    token_number = 1000 + i

    lines.append(
        f"STUDENT_{student_id}_TOKEN=student-demo-token-{token_number}"
    )

lines.append("TEACHER_TOKEN=teacher-demo-token-2026")

env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("Updated .env successfully.")
print("Student tokens generated: 100")
print("Teacher token generated: 1")
