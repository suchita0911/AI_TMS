"""End-to-end integration flow covering all phases (ordered)."""
import pytest

from app.core.config import settings
from tests.conftest import auth

API = settings.API_V1_PREFIX

MATERIAL = (
    "Information Security Policy Overview. "
    "All employees must use strong passwords with at least twelve characters. "
    "Confidential data must never be shared over public email systems. "
    "Phishing emails should be reported to the security team immediately. "
    "Multi factor authentication is mandatory for all corporate accounts. "
    "Devices must be locked when left unattended in the office. "
    "Security incidents must be reported within twenty four hours of discovery. "
    "Access to production systems requires manager approval and periodic review. "
)


@pytest.fixture(scope="module")
def state():
    return {}


class TestFullFlow:
    def test_register_creates_pending_account_and_emails_setup_link(self, client, state):
        # Self-registration collects no password: the account starts PENDING and
        # the user gets a one-time link (returned here only because DEBUG=true).
        r = client.post(f"{API}/auth/register", json={
            "first_name": "Ada", "last_name": "Lovelace", "username": "ada.flow",
            "email": "ada.flow@corp.local",
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["user"]["status"] == "pending"
        assert data["setup_token"]
        state["setup_token"] = data["setup_token"]

    def test_pending_account_cannot_login_before_set_password(self, client, state):
        r = client.post(f"{API}/auth/login", json={"username": "ada.flow", "password": "Ada@12345"})
        assert r.status_code == 401

    def test_set_password_then_login(self, client, state):
        r = client.post(f"{API}/auth/set-password", json={
            "token": state["setup_token"], "new_password": "Ada@12345",
        })
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "active"

        r = client.post(f"{API}/auth/login", json={"username": "ada.flow", "password": "Ada@12345"})
        assert r.status_code == 200
        state["emp_token"] = r.json()["access_token"]
        state["emp_id"] = r.json()["user"]["id"]

    def test_rbac_employee_forbidden(self, client, state):
        r = client.get(f"{API}/users", headers=auth(state["emp_token"]))
        assert r.status_code == 403

    def test_admin_creates_course(self, client, admin_token, state):
        r = client.post(f"{API}/courses", headers=auth(admin_token), json={
            "name": "InfoSec Awareness", "description": "Security basics",
            "category": "Compliance", "course_type": "mandatory",
            "passing_percentage": 50, "quiz_question_count": 6,
            "allow_retry": True, "retry_count": 2,
        })
        assert r.status_code == 201, r.text
        state["course_id"] = r.json()["id"]

    def test_upload_and_extract(self, client, admin_token, state):
        r = client.post(
            f"{API}/courses/{state['course_id']}/documents",
            headers=auth(admin_token),
            files={"file": ("infosec.txt", MATERIAL, "text/plain")},
        )
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "processed"
        assert r.json()["text_chars"] > 0

    def test_publish_requires_material_then_succeeds(self, client, admin_token, state):
        r = client.post(f"{API}/courses/{state['course_id']}/publish", headers=auth(admin_token))
        assert r.status_code == 200
        assert r.json()["status"] == "published"

    def test_mandatory_course_auto_assigned_on_publish(self, client, admin_token, state):
        # The course is mandatory, so publishing auto-enrolls all active employees.
        r = client.get(f"{API}/courses/{state['course_id']}/enrollments", headers=auth(admin_token))
        assert r.status_code == 200
        assert any(e["user"]["id"] == state["emp_id"] for e in r.json())

    def test_generate_questions(self, client, admin_token, state):
        import time

        r = client.post(
            f"{API}/courses/{state['course_id']}/generate-questions",
            headers=auth(admin_token), json={"count": 20, "replace_existing": True},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "running"

        # Poll the background job until it completes.
        deadline = time.time() + 180
        status = "running"
        while time.time() < deadline:
            s = client.get(
                f"{API}/courses/{state['course_id']}/generation-status",
                headers=auth(admin_token),
            ).json()
            status = s["status"]
            if status in ("done", "error"):
                break
            time.sleep(2)
        assert status == "done", f"generation did not finish: {status}"
        assert s.get("generated", 0) > 0

    def test_assign_to_employee(self, client, admin_token, state):
        # Explicit individual assignment. Because the mandatory course already
        # auto-enrolled this employee on publish, the endpoint reports them as
        # already assigned (idempotent) — total targeted is still 1.
        r = client.post(
            f"{API}/courses/{state['course_id']}/assign",
            headers=auth(admin_token),
            json={"target_type": "individual", "user_ids": [state["emp_id"]]},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_targeted"] == 1
        assert data["assigned"] + data["already_assigned"] == 1

    def test_employee_sees_assigned_course(self, client, state):
        r = client.get(f"{API}/me/courses", headers=auth(state["emp_token"]))
        assert r.status_code == 200
        courses = r.json()
        assert any(c["course_id"] == state["course_id"] for c in courses)

    def test_assignment_notification_created(self, client, state):
        r = client.get(f"{API}/me/notifications", headers=auth(state["emp_token"]))
        assert r.status_code == 200
        assert any(n["type"] == "assigned" for n in r.json())

    def test_quiz_flow_pass_and_complete(self, client, admin_token, state):
        cid = state["course_id"]
        # answer key from admin
        bank = client.get(f"{API}/courses/{cid}/questions?page_size=100",
                          headers=auth(admin_token)).json()["items"]
        key = {q["id"]: q["correct_answer"] for q in bank}

        client.post(f"{API}/me/courses/{cid}/complete-content", headers=auth(state["emp_token"]))
        quiz = client.post(f"{API}/me/courses/{cid}/quiz/start", headers=auth(state["emp_token"])).json()
        # correct answers must not be exposed
        assert all("correct_answer" not in q for q in quiz["questions"])
        answers = [{"answer_id": q["answer_id"], "selected": key[q["question_id"]]}
                   for q in quiz["questions"]]
        result = client.post(f"{API}/me/quiz/{quiz['attempt_id']}/submit",
                             headers=auth(state["emp_token"]), json={"answers": answers}).json()
        assert result["passed"] is True
        assert result["score_percentage"] == 100.0

    def test_certificate_issued_and_verifiable(self, client, state):
        cid = state["course_id"]
        cert = client.get(f"{API}/me/courses/{cid}/certificate", headers=auth(state["emp_token"]))
        assert cert.status_code == 200, cert.text
        number = cert.json()["certificate_number"]

        pdf = client.get(f"{API}/me/courses/{cid}/certificate/download", headers=auth(state["emp_token"]))
        assert pdf.status_code == 200
        assert pdf.content[:5] == b"%PDF-"

        verify = client.get(f"{API}/certificates/verify/{number}")
        assert verify.status_code == 200
        assert verify.json()["valid"] is True

    def test_reports_overview(self, client, admin_token):
        r = client.get(f"{API}/reports/overview", headers=auth(admin_token))
        assert r.status_code == 200
        assert r.json()["completed"] >= 1

    def test_report_excel_export(self, client, admin_token):
        r = client.get(f"{API}/reports/export/excel", headers=auth(admin_token))
        assert r.status_code == 200
        assert r.content[:2] == b"PK"  # xlsx is a zip
