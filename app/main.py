
import json
import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(
    title="Secure Student Records & Academic Insights API",
    description=(
        "A security-focused academic analysis API using "
        "synthetic student records, API-key authentication, "
        "and role-based access control."
    ),
    version="1.0.0",
)

# --------------------------------------------------
# 2. LOAD THE 100 SYNTHETIC STUDENT RECORDS
# --------------------------------------------------

DATA_FILE = BASE_DIR / "data" / "students.json"

with DATA_FILE.open("r", encoding="utf-8") as file:
    STUDENTS = json.load(file)

STUDENTS_BY_ID = {
    student["student_id"]: student
    for student in STUDENTS
}

# --------------------------------------------------
# 3. LOAD STUDENT AND TEACHER IDENTITIES
# --------------------------------------------------
# Load user tokens from Secret Manager in Cloud Run.
# For local development, fall back to the tokens in .env.
token_map_json = os.getenv("USER_TOKENS_JSON")

if token_map_json:
    USER_TOKENS = json.loads(token_map_json)
else:
    USER_TOKENS = {}

    for i in range(1, 101):
        student_id = f"S{1000 + i}"
        token_variable = f"STUDENT_{student_id}_TOKEN"
        token = os.getenv(token_variable)

        if token:
            USER_TOKENS[token] = {
                "user_id": student_id,
                "role": "student",
            }

    teacher_token = os.getenv("TEACHER_TOKEN")

    if teacher_token:
        USER_TOKENS[teacher_token] = {
            "user_id": "T1001",
            "role": "teacher",
        }

teacher_token_configured = any(
    user["role"] == "teacher"
    for user in USER_TOKENS.values()
)

# --------------------------------------------------
# 4. REQUEST VALIDATION
# --------------------------------------------------

class InsightRequest(BaseModel):
    target_marks: int = Field(default=75, ge=0, le=100)


# --------------------------------------------------
# 5. API-KEY AUTHENTICATION
# --------------------------------------------------

def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
):
    expected_key = os.getenv("API_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="API key is not configured on the server.",
        )

    if x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key.",
        )


# --------------------------------------------------
# 6. USER AUTHENTICATION
# --------------------------------------------------

def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    user = USER_TOKENS.get(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid user token.",
        )

    return user


# --------------------------------------------------
# 7. SECURITY DEPENDENCIES
# --------------------------------------------------

def require_security(
    _: Annotated[None, Depends(verify_api_key)],
):
    return True


def require_user(
    _: Annotated[None, Depends(verify_api_key)],
    user: Annotated[dict, Depends(get_current_user)],
):
    return user


# --------------------------------------------------
# 8. HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    # Public health check; never return credentials or tokens.
    return {"status": "healthy"}


# --------------------------------------------------
# 9. GET THE LOGGED-IN STUDENT'S OWN RECORD
# --------------------------------------------------

@app.get("/students/me")
def get_my_record(
    user: Annotated[dict, Depends(require_user)],
):
    if user["role"] != "student":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for student accounts.",
        )

    student = STUDENTS_BY_ID.get(user["user_id"])

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student record not found.",
        )

    return student


# --------------------------------------------------
# 10. GET A SPECIFIC STUDENT RECORD
# --------------------------------------------------

@app.get("/students/{student_id}")
def get_student_record(
    student_id: str,
    user: Annotated[dict, Depends(require_user)],
):
    student = STUDENTS_BY_ID.get(student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student record not found.",
        )

    # Students may only access their own records.
    # Teachers may access student records in this demo.
    if (
        user["role"] == "student"
        and user["user_id"] != student_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to access this student's record.",
        )

    if user["role"] not in {"student", "teacher"}:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions.",
        )

    return student


# --------------------------------------------------
# 11. ACADEMIC INSIGHTS AND RECOMMENDATIONS
# --------------------------------------------------

@app.get("/students/{student_id}/insights")
def get_student_insights(
    student_id: str,
    user: Annotated[dict, Depends(require_user)],
    target_marks: int = 75,
):
    # Validate the target before performing analysis.
    if not 0 <= target_marks <= 100:
        raise HTTPException(
            status_code=422,
            detail="target_marks must be between 0 and 100.",
        )

    student = STUDENTS_BY_ID.get(student_id)

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student record not found.",
        )

    # Enforce record-level authorization.
    if (
        user["role"] == "student"
        and user["user_id"] != student_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot view another student's insights.",
        )

    if user["role"] not in {"student", "teacher"}:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions.",
        )

    marks = student["marks"]

    if not marks:
        raise HTTPException(
            status_code=422,
            detail="No marks are available for analysis.",
        )

    # Academic analysis using transparent rules.
    average = round(sum(marks.values()) / len(marks), 2)

    needs_attention = [
        subject
        for subject, score in marks.items()
        if score < target_marks
    ]

    if needs_attention:
        recommendation = (
            "Focus revision on: "
            + ", ".join(needs_attention)
        )
    else:
        recommendation = (
            "Maintain your current performance and "
            "practise advanced questions."
        )

    return {
        "student_id": student_id,
        "subject_marks": marks,
        "overall_average": average,
        "target_marks": target_marks,
        "subjects_below_target": needs_attention,
        "recommendation": recommendation,
        "note": (
            "Recommendations are generated using transparent "
            "rules, not a trained machine-learning model."
        ),
    }


# --------------------------------------------------
# 12. TEACHER-ONLY CLASS SUMMARY
# --------------------------------------------------

@app.get("/teacher/class-summary")
def get_class_summary(
    user: Annotated[dict, Depends(require_user)],
):
    if user["role"] != "teacher":
        raise HTTPException(
            status_code=403,
            detail="Teacher permission is required.",
        )

    summary = []

    for student in STUDENTS:
        marks = student["marks"]

        if not marks:
            average = None
        else:
            average = round(
                sum(marks.values()) / len(marks), 2
            )

        summary.append({
            "student_id": student["student_id"],
            "overall_average": average,
            "attendance": student["attendance"],
        })

    return {
        "class_size": len(summary),
        "students": summary,
    }


# --------------------------------------------------
# 13. SECURITY STATUS
# --------------------------------------------------

@app.get("/security/status")
def security_status(
    _: Annotated[None, Depends(require_security)],
):
    # Report control status without disclosing secrets.
    return {
        "api_key_required": True,
        "user_token_required_for_records": True,
        "role_based_access_control": True,
        "input_validation": True,
        "student_records_loaded": len(STUDENTS),
        "student_tokens_configured": sum(
            1
            for user in USER_TOKENS.values()
            if user["role"] == "student"
        ),
        "teacher_token_configured": teacher_token_configured,
        "secret_values_exposed": False,
    }
