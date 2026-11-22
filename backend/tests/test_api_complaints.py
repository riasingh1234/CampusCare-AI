"""Features 1, 4, 5, 6, 7 and 8 through the real endpoint functions. Only the database, Blob Storage and Foundry are faked."""
import json
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import azure.functions as func

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api.admin as admin_api  # noqa: E402
import api.complaints as api  # noqa: E402
from core.config import AiSettings  # noqa: E402
from core.security import create_access_token  # noqa: E402
from tests.fakes import NOW, SETTINGS, FakeComplaints, FakeReference  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
GOOD = {"title": "Tap leaking in washroom", "description": "The tap near the ground floor washroom has been leaking since Monday.",
        "categoryId": 2, "location": "Academic Block A"}


def token_for(user_id, role):
    return create_access_token(user_id, role, SETTINGS)[0]


ADMIN, RAVI, ANIL, AARAV, ISHITA = (token_for(1, "admin"), token_for(2, "staff"), token_for(3, "staff"),
                                    token_for(4, "student"), token_for(5, "student"))


def call(endpoint, token=None, body=None, method="POST", route_params=None, params=None, raw=None, headers=None):
    h = dict(headers or {})
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
    req = func.HttpRequest(method=method, url="/api/x", headers=h, body=data, route_params=route_params or {}, params=params or {})
    res = endpoint.build().get_user_function()(req)
    return res.status_code, json.loads(res.get_body() or b"{}")


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.repo, self.ref = FakeComplaints(), FakeReference()
        self.uploaded = []

        @contextmanager
        def fake_repos():
            yield self.repo, self.ref

        def fake_upload(name, data, content_type):
            self.uploaded.append((name, len(data), content_type))

        patches = [
            patch.object(api, "open_repos", fake_repos), patch.object(admin_api, "open_repos", fake_repos),
            patch("core.auth_guard.get_app_settings", return_value=SETTINGS),
            patch.object(api, "upload_blob", fake_upload),
            patch.object(api, "make_read_urls", lambda names: {n: f"https://blob.example/{n}?sas=1" for n in names}),
            patch("services.classifier.get_ai_settings", return_value=AiSettings(False, "entra", None, None, None, None)),
            patch("services.complaint_service.utc_now", return_value=NOW),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def submit(self, token=AARAV, **extra):
        return call(api.submit, token, {**GOOD, **extra})

    def submit_and_assign(self, staff=2, dept=1, priority="High"):
        _, created = self.submit()
        ref = created["id"]
        call(api.assign, ADMIN, {"departmentId": dept, "staffId": staff, "priority": priority}, route_params={"reference": ref})
        return ref


class SubmissionTests(ApiTestCase):
    def test_student_submits_and_gets_a_reference(self):
        status, body = self.submit()
        self.assertEqual(status, 201)
        self.assertEqual((body["id"], body["status"], body["priority"], body["aiSource"]), ("CC-2026-0001", "Submitted", "Medium", "rules"))
        self.assertEqual(self.repo.history[0]["status"], "Submitted")
        self.assertEqual(self.repo.rows[0]["aiSuggestion"]["source"], "rules")
        self.assertEqual(self.repo.rows[0]["dueAt"], NOW + 96 * __import__("datetime").timedelta(hours=1))  # Medium = 96 hours

    def test_safety_wording_sets_critical_and_a_shorter_deadline(self):
        _, body = self.submit(description="The ceiling fan threw sparks and gave off a burning smell this morning.", categoryId=1)
        self.assertEqual(body["priority"], "Critical")
        self.assertEqual(self.repo.rows[0]["dueAt"] - NOW, __import__("datetime").timedelta(hours=24))

    def test_falls_back_to_category_default_when_nothing_is_suggested(self):
        _, body = self.submit(title="Something odd about this", description="Please look at the situation near the cafeteria soon.", categoryId=4)
        self.assertEqual((body["priority"], body["aiSource"]), ("Low", None))

    def test_validation_errors_name_the_fields(self):
        status, body = call(api.submit, AARAV, {"title": "x", "description": "short", "location": "", "categoryId": ""})
        self.assertEqual(status, 400)
        self.assertEqual(set(body["error"]["details"]), {"title", "description", "location", "categoryId"})

    def test_unknown_category_is_rejected(self):
        status, body = self.submit(categoryId=999)
        self.assertEqual((status, "categoryId" in body["error"]["details"]), (400, True))

    def test_only_students_can_submit(self):
        self.assertEqual(self.submit(token=RAVI)[0], 403)
        self.assertEqual(self.submit(token=ADMIN)[0], 403)

    def test_must_be_signed_in(self):
        self.assertEqual(call(api.submit, None, GOOD)[0], 401)
        self.assertEqual(call(api.submit, "garbage", GOOD)[0], 401)

    def test_numeric_text_id_is_accepted(self):
        self.assertEqual(self.submit(categoryId="2")[0], 201)


class ClassifyAndDuplicateTests(ApiTestCase):
    def test_classify_endpoint_returns_suggestion(self):
        status, body = call(api.classify_text, AARAV, {"title": "Wifi down", "description": "The internet in the lab is not working at all."})
        self.assertEqual(status, 200)
        self.assertEqual((body["suggestion"]["categoryId"], body["suggestion"]["source"]), (3, "rules"))

    def test_classify_short_text_gives_null(self):
        self.assertEqual(call(api.classify_text, AARAV, {"title": "", "description": "hi"})[1], {"suggestion": None})

    def test_classify_requires_sign_in(self):
        self.assertEqual(call(api.classify_text, None, {"title": "a", "description": "b"})[0], 401)

    def test_duplicate_warning_does_not_block_submission(self):
        self.submit()
        status, body = call(api.duplicates, ISHITA, {"title": "Leaking tap in washroom", "location": "Academic Block A",
                                                      "description": "The washroom tap on the ground floor is leaking badly."})
        self.assertEqual(status, 200)
        self.assertEqual(len(body["duplicates"]), 1)
        self.assertEqual(body["duplicates"][0]["id"], "CC-2026-0001")
        self.assertEqual(self.submit(token=ISHITA)[0], 201)   # a second, similar complaint is still accepted
        self.assertEqual(len(self.repo.rows), 2)


class AssignmentAndStatusTests(ApiTestCase):
    def test_admin_assigns_and_history_is_recorded(self):
        ref = self.submit_and_assign()
        row = self.repo.rows[0]
        self.assertEqual((row["status"], row["assignedStaffId"], row["departmentId"], row["priority"]), ("Assigned", 2, 1, "High"))
        self.assertEqual(row["dueAt"] - row["createdAt"], __import__("datetime").timedelta(hours=48))
        self.assertIn("Ravi Electrician", self.repo.history[-1]["note"])
        self.assertTrue(ref)

    def test_staff_must_belong_to_the_department(self):
        _, created = self.submit()
        status, body = call(api.assign, ADMIN, {"departmentId": 1, "staffId": 3, "priority": "High"}, route_params={"reference": created["id"]})
        self.assertEqual((status, "staffId" in body["error"]["details"]), (400, True))

    def test_only_admin_can_assign(self):
        _, created = self.submit()
        for token in (AARAV, RAVI):
            self.assertEqual(call(api.assign, token, {"departmentId": 1, "staffId": 2, "priority": "High"},
                                  route_params={"reference": created["id"]})[0], 403)

    def test_bad_reference_is_404(self):
        self.assertEqual(call(api.assign, ADMIN, {"departmentId": 1, "staffId": 2, "priority": "High"}, route_params={"reference": "nope"})[0], 404)
        self.assertEqual(call(api.assign, ADMIN, {"departmentId": 1, "staffId": 2, "priority": "High"}, route_params={"reference": "CC-2026-0099"})[0], 404)

    def test_reassign_keeps_status_and_changes_staff(self):
        ref = self.submit_and_assign()
        call(api.update_status, RAVI, {"status": "In Progress"}, route_params={"reference": ref})
        call(api.assign, ADMIN, {"departmentId": 2, "staffId": 3, "priority": "High"}, route_params={"reference": ref})
        self.assertEqual((self.repo.rows[0]["status"], self.repo.rows[0]["assignedStaffId"]), ("In Progress", 3))

    def test_staff_moves_through_the_statuses_and_history_grows(self):
        ref = self.submit_and_assign()
        rp = {"reference": ref}
        self.assertEqual(call(api.update_status, RAVI, {"status": "In Progress", "note": ""}, route_params=rp)[0], 200)
        self.assertEqual(self.repo.history[-1]["note"], "Work started.")
        self.assertEqual(call(api.update_status, RAVI, {"status": "Resolved", "note": "Replaced the socket and tested."}, route_params=rp)[0], 200)
        row = self.repo.rows[0]
        self.assertEqual((row["status"], row["resolutionNote"]), ("Resolved", "Replaced the socket and tested."))
        self.assertEqual([h["status"] for h in self.repo.history], ["Submitted", "Assigned", "In Progress", "Resolved"])

    def test_resolving_needs_a_real_note(self):
        ref = self.submit_and_assign()
        status, body = call(api.update_status, RAVI, {"status": "Resolved", "note": "done"}, route_params={"reference": ref})
        self.assertEqual((status, "note" in body["error"]["details"]), (400, True))

    def test_cannot_skip_backwards_or_edit_resolved(self):
        ref = self.submit_and_assign()
        rp = {"reference": ref}
        call(api.update_status, RAVI, {"status": "Resolved", "note": "Fixed it properly today."}, route_params=rp)
        self.assertEqual(call(api.update_status, RAVI, {"status": "In Progress"}, route_params=rp)[0], 409)
        self.assertEqual(call(api.assign, ADMIN, {"departmentId": 1, "staffId": 2, "priority": "Low"}, route_params=rp)[0], 409)

    def test_unassigned_complaint_cannot_be_progressed(self):
        _, created = self.submit()
        self.assertEqual(call(api.update_status, ADMIN, {"status": "In Progress"}, route_params={"reference": created["id"]})[0], 409)

    def test_other_staff_cannot_update(self):
        ref = self.submit_and_assign()
        self.assertEqual(call(api.update_status, ANIL, {"status": "In Progress"}, route_params={"reference": ref})[0], 404)

    def test_student_cannot_update_status(self):
        ref = self.submit_and_assign()
        self.assertEqual(call(api.update_status, AARAV, {"status": "Resolved", "note": "I fixed it myself."}, route_params={"reference": ref})[0], 403)


class WorkspaceVisibilityTests(ApiTestCase):
    def test_each_role_sees_only_its_own_complaints(self):
        ref = self.submit_and_assign()
        self.submit(token=ISHITA)
        def refs(token):
            status, body = call(api.workspace, token, method="GET")
            self.assertEqual(status, 200)
            return [c["id"] for c in body["complaints"]], body
        self.assertEqual(refs(AARAV)[0], [ref])
        self.assertEqual(refs(ISHITA)[0], ["CC-2026-0002"])
        self.assertEqual(refs(RAVI)[0], [ref])
        self.assertEqual(refs(ANIL)[0], [])
        self.assertEqual(sorted(refs(ADMIN)[0]), ["CC-2026-0001", "CC-2026-0002"])

    def test_history_is_limited_the_same_way_and_has_no_internal_ids(self):
        ref = self.submit_and_assign()
        self.submit(token=ISHITA)
        _, body = call(api.workspace, AARAV, method="GET")
        self.assertTrue(all(h["complaintId"] == ref for h in body["history"]))
        self.assertNotIn("dbId", body["complaints"][0])

    def test_student_does_not_get_other_students_names(self):
        _, body = call(api.workspace, AARAV, method="GET")
        names = {u["name"] for u in body["users"]}
        self.assertIn("Aarav Student", names)
        self.assertNotIn("Ishita Student", names)
        self.assertTrue(all("email" not in u for u in body["users"]))

    def test_must_be_signed_in(self):
        self.assertEqual(call(api.workspace, None, method="GET")[0], 401)


class FeedbackTests(ApiTestCase):
    def resolve(self):
        ref = self.submit_and_assign()
        call(api.update_status, RAVI, {"status": "Resolved", "note": "Replaced the part and tested."}, route_params={"reference": ref})
        return {"reference": ref}

    def test_student_rates_a_resolved_complaint_once(self):
        rp = self.resolve()
        self.assertEqual(call(api.feedback, AARAV, {"rating": 5, "comment": "Thanks"}, route_params=rp)[0], 201)
        self.assertEqual(call(api.feedback, AARAV, {"rating": 4}, route_params=rp)[0], 409)

    def test_cannot_rate_before_resolved(self):
        ref = self.submit_and_assign()
        self.assertEqual(call(api.feedback, AARAV, {"rating": 5}, route_params={"reference": ref})[0], 409)

    def test_other_student_cannot_rate(self):
        self.assertEqual(call(api.feedback, ISHITA, {"rating": 5}, route_params=self.resolve())[0], 404)

    def test_rating_must_be_1_to_5(self):
        for bad in (0, 6, "5", None, True):
            self.assertEqual(call(api.feedback, AARAV, {"rating": bad}, route_params=self.resolve())[0], 400, bad)


class AttachmentTests(ApiTestCase):
    def upload(self, token, ref, data=PNG, ctype="image/png", name="leak.png"):
        return call(api.upload_attachment, token, raw=data, route_params={"reference": ref}, params={"name": name}, headers={"Content-Type": ctype})

    def test_student_uploads_an_image_to_blob_and_name_is_saved(self):
        _, created = self.submit()
        status, body = self.upload(AARAV, created["id"], name="C:\\Users\\me\\leak photo.png")
        self.assertEqual((status, body["type"]), (201, "image/png"))
        blob_name, size, ctype = self.uploaded[0]
        self.assertTrue(blob_name.startswith("complaints/1/") and blob_name.endswith(".png"))
        self.assertNotIn("leak", blob_name)  # the student's file name is never used in the blob name
        self.assertEqual((self.repo.files[0]["name"], self.repo.files[0]["type"]), ("leak photo.png", "image/png"))

    def test_workspace_returns_attachment_links(self):
        _, created = self.submit()
        self.upload(AARAV, created["id"])
        _, body = call(api.workspace, AARAV, method="GET")
        self.assertTrue(body["complaints"][0]["attachments"][0]["url"].startswith("https://blob.example/complaints/1/"))

    def test_wrong_content_is_rejected_even_with_an_image_header(self):
        _, created = self.submit()
        status, _ = self.upload(AARAV, created["id"], data=b"<html>not an image</html>", ctype="image/png")
        self.assertEqual((status, self.uploaded), (400, []))

    def test_mismatched_declared_type_is_rejected(self):
        _, created = self.submit()
        self.assertEqual(self.upload(AARAV, created["id"], ctype="application/pdf")[0], 400)

    def test_pdf_is_allowed(self):
        _, created = self.submit()
        self.assertEqual(self.upload(AARAV, created["id"], data=b"%PDF-1.7 data", ctype="application/pdf", name="proof.pdf")[0], 201)

    def test_too_big_is_rejected(self):
        _, created = self.submit()
        self.assertEqual(self.upload(AARAV, created["id"], data=PNG + b"0" * (5 * 1024 * 1024))[0], 413)

    def test_empty_is_rejected(self):
        _, created = self.submit()
        self.assertEqual(self.upload(AARAV, created["id"], data=b"")[0], 400)

    def test_other_student_cannot_upload(self):
        _, created = self.submit()
        self.assertEqual(self.upload(ISHITA, created["id"])[0], 404)

    def test_limit_per_complaint(self):
        _, created = self.submit()
        for _ in range(5):
            self.assertEqual(self.upload(AARAV, created["id"])[0], 201)
        self.assertEqual(self.upload(AARAV, created["id"])[0], 409)

    def test_blob_failure_means_no_database_row(self):
        _, created = self.submit()
        with patch.object(api, "upload_blob", side_effect=RuntimeError("storage down")):
            status, body = self.upload(AARAV, created["id"])
        self.assertEqual((status, self.repo.files), (500, []))
        self.assertNotIn("storage down", json.dumps(body))


class AdminTests(ApiTestCase):
    def test_analytics_uses_repository_data(self):
        ref = self.submit_and_assign()
        call(api.update_status, RAVI, {"status": "Resolved", "note": "Replaced the part and tested."}, route_params={"reference": ref})
        self.submit(token=ISHITA)
        status, body = call(admin_api.analytics, ADMIN, method="GET", params={"tz": "330"})
        self.assertEqual(status, 200)
        self.assertEqual((body["summary"]["total"], body["summary"]["resolved"], body["summary"]["open"]), (2, 1, 1))
        self.assertEqual(len(body["trend"]), 30)

    def test_analytics_admin_only(self):
        for token in (AARAV, RAVI, None):
            self.assertIn(call(admin_api.analytics, token, method="GET")[0], (401, 403))

    def test_bad_tz_is_ignored(self):
        self.assertEqual(call(admin_api.analytics, ADMIN, method="GET", params={"tz": "abc"})[0], 200)

    def test_manual_escalation_button_and_no_duplicates(self):
        self.submit()
        self.repo.rows[0]["dueAt"] = NOW - __import__("datetime").timedelta(hours=3)   # make it overdue
        with patch("services.escalation.utc_now", return_value=NOW):
            first = call(admin_api.run_escalation_now, ADMIN)
            second = call(admin_api.run_escalation_now, ADMIN)
        self.assertEqual((first[0], first[1]["newEscalations"]), (200, 1))
        self.assertEqual((second[1]["newEscalations"], second[1]["alreadyEscalated"]), (0, 1))
        self.assertTrue(self.repo.rows[0]["isEscalated"])

    def test_only_admin_can_run_escalation(self):
        self.assertEqual(call(admin_api.run_escalation_now, RAVI)[0], 403)
        self.assertEqual(call(admin_api.run_escalation_now, AARAV)[0], 403)

    def test_department_crud(self):
        status, body = call(admin_api.add_department, ADMIN, {"name": "Transport"})
        self.assertEqual(status, 201)
        new_id = body["id"]
        self.assertEqual(call(admin_api.add_department, ADMIN, {"name": "transport"})[0], 409)
        self.assertEqual(call(admin_api.edit_department, ADMIN, {"name": "Campus Transport"}, method="PUT", route_params={"id": str(new_id)})[0], 200)
        self.ref.used_departments.add(1)
        self.assertEqual(call(admin_api.remove_department, ADMIN, method="DELETE", route_params={"id": "1"})[0], 409)
        self.assertEqual(call(admin_api.remove_department, ADMIN, method="DELETE", route_params={"id": str(new_id)})[0], 200)
        self.assertEqual(call(admin_api.remove_department, ADMIN, method="DELETE", route_params={"id": "abc"})[0], 404)

    def test_category_crud_and_keyword_cleaning(self):
        status, body = call(admin_api.add_category, ADMIN, {"name": "Transport", "departmentId": 1, "defaultPriority": "Low",
                                                            "keywords": " Bus , bus,  Shuttle ,"})
        self.assertEqual(status, 201)
        self.assertEqual(next(c for c in self.ref.cats if c["id"] == body["id"])["keywords"], ["bus", "shuttle"])
        self.assertEqual(call(admin_api.add_category, ADMIN, {"name": "X1", "departmentId": 999, "defaultPriority": "Low", "keywords": ""})[0], 400)
        self.ref.used_categories.add(1)
        self.assertEqual(call(admin_api.remove_category, ADMIN, method="DELETE", route_params={"id": "1"})[0], 409)

    def test_admin_crud_is_admin_only(self):
        self.assertEqual(call(admin_api.add_department, AARAV, {"name": "Hack"})[0], 403)
        self.assertEqual(call(admin_api.add_category, RAVI, {"name": "Hack", "departmentId": 1, "defaultPriority": "Low"})[0], 403)


if __name__ == "__main__":
    unittest.main()
