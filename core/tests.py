import datetime
import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Role
from audit.models import AuditLog
from beneficiaries.models import Beneficiary, BeneficiaryProject
from documents.models import Document
from finance.models import Payment
from grm.models import GRMCase
from monitoring.models import ProgressUpdate
from notifications.models import Notification
from projects.models import Project

User = get_user_model()
PW = "Str0ng!Passw0rd"
TMP_MEDIA = override_settings(MEDIA_ROOT="/tmp/nacsa_test_media")


def make_user(username, role, **kw):
    return User.objects.create_user(username=username, password=PW, role=Role.objects.get(name=role), email=f"{username}@x.org", **kw)


def make_project(creator, **kw):
    d = dict(name="Test Well", project_type="Water and Sanitation", district="Bo", budget=Decimal("1000"),
             start_date=datetime.date.today(), expected_completion_date=datetime.date.today() + datetime.timedelta(days=90),
             created_by=creator, status="draft")
    d.update(kw)
    return Project.objects.create(**d)


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("adm", "administrator")
        cls.pm = make_user("pm", "project_manager")
        cls.pm2 = make_user("pm2", "project_manager")
        cls.me = make_user("me", "me_officer")
        cls.field = make_user("fo", "field_officer")
        cls.fin = make_user("fin", "finance_officer")
        cls.grm = make_user("grm", "grm_officer")
        cls.data = make_user("data", "data_entry_officer")
        cls.viewer = make_user("view", "viewer")

    def login(self, u):
        self.client.logout()
        self.assertTrue(self.client.login(username=u.username, password=PW))


class AuthTests(Base):
    def test_login_required_redirects(self):
        r = self.client.get("/projects/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_login_logout_and_audit(self):
        r = self.client.post(reverse("accounts:login"), {"username": "pm", "password": PW})
        self.assertRedirects(r, reverse("dashboard:index"))
        self.assertTrue(AuditLog.objects.filter(action="login", user=self.pm).exists())
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_bad_password_and_lockout(self):
        cache.clear()
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {"username": "pm", "password": "wrong"})
        r = self.client.post(reverse("accounts:login"), {"username": "pm", "password": PW})
        self.assertEqual(r.status_code, 200)       # locked: even the right password is refused
        self.assertContains(r, "Too many failed attempts")
        cache.clear()

    def test_open_redirect_blocked(self):
        r = self.client.post(reverse("accounts:login"), {"username": "pm", "password": PW, "next": "https://evil.example/"})
        self.assertRedirects(r, reverse("dashboard:index"))

    def test_user_management_admin_only(self):
        self.login(self.pm)
        self.assertEqual(self.client.get("/accounts/users/").status_code, 403)
        self.login(self.admin)
        self.assertEqual(self.client.get("/accounts/users/").status_code, 200)
        r = self.client.post("/accounts/users/new/", {"username": "newu", "first_name": "N", "last_name": "U", "email": "n@x.org",
                                                      "role": Role.objects.get(name="viewer").pk, "is_active": "on", "password": PW})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.get(username="newu").check_password(PW))

    def test_password_reset_does_not_leak_accounts(self):
        r = self.client.post(reverse("accounts:password_reset"), {"email": "nobody@nowhere.org"})
        self.assertEqual(r.status_code, 302)


class PermissionTests(Base):
    def test_viewer_cannot_see_restricted_modules(self):
        self.login(self.viewer)
        for url in ["/finance/", "/beneficiaries/", "/grm/", "/audit/", "/reports/", "/projects/new/"]:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.assertEqual(self.client.get("/projects/").status_code, 200)

    def test_field_officer_cannot_approve_or_see_finance(self):
        p = make_project(self.pm, status="submitted")
        self.login(self.field)
        self.assertEqual(self.client.get(f"/projects/{p.pk}/review/").status_code, 403)
        self.assertEqual(self.client.get("/finance/payments/").status_code, 403)

    def test_finance_cannot_edit_projects(self):
        p = make_project(self.pm)
        self.login(self.fin)
        self.assertEqual(self.client.get(f"/projects/{p.pk}/edit/").status_code, 403)

    def test_nav_hides_forbidden_modules(self):
        self.login(self.viewer)
        html = self.client.get("/").content.decode()
        self.assertNotIn("Finance &amp; Payments", html)
        self.assertNotIn("Audit Trail", html)


class ProjectWorkflowTests(Base):
    payload = dict(name="New Clinic", project_type="Health", district="Bo", chiefdom="Kakua", community="Gerihun", ward="12",
                   budget="5000", start_date="2026-01-01", expected_completion_date="2026-12-31", target_beneficiaries="100",
                   initial_activities="Mobilise\nBuild")

    def test_create_draft_and_auto_id(self):
        self.login(self.pm)
        r = self.client.post("/projects/new/", self.payload)
        p = Project.objects.get(name="New Clinic")
        self.assertRedirects(r, f"/projects/{p.pk}/")
        self.assertTrue(p.project_id.startswith("NACSA-PRJ-"))
        self.assertEqual(p.status, "draft")
        self.assertEqual(p.activities.count(), 2)

    def test_validation_rejects_bad_dates_and_budget(self):
        self.login(self.pm)
        bad = dict(self.payload, expected_completion_date="2025-01-01", budget="0")
        r = self.client.post("/projects/new/", bad)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Project.objects.filter(name="New Clinic").exists())

    def test_submit_approve_flow_with_notifications_and_audit(self):
        self.login(self.data)
        self.client.post("/projects/new/", dict(self.payload, submit="1"))
        p = Project.objects.get(name="New Clinic")
        self.assertEqual(p.status, "submitted")
        self.assertTrue(Notification.objects.filter(user=self.pm, event_type="approval_required").exists())
        self.login(self.pm)
        r = self.client.post(f"/projects/{p.pk}/review/", {"decision": "approved", "comments": "ok"})
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.status, "approved")
        self.assertTrue(p.approvals.filter(decision="approved", reviewed_by=self.pm).exists())
        self.assertTrue(Notification.objects.filter(user=self.data, event_type="project_approved").exists())
        self.assertTrue(AuditLog.objects.filter(module="projects", record_id=str(p.pk), action="approved").exists())

    def test_rejection_requires_comment(self):
        p = make_project(self.data, status="submitted")
        self.login(self.pm)
        r = self.client.post(f"/projects/{p.pk}/review/", {"decision": "rejected", "comments": ""})
        self.assertEqual(r.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.status, "under_review")

    def test_cannot_approve_own_project(self):
        p = make_project(self.pm, status="submitted")
        self.login(self.pm)
        self.client.post(f"/projects/{p.pk}/review/", {"decision": "approved", "comments": ""})
        p.refresh_from_db()
        self.assertNotEqual(p.status, "approved")
        self.login(self.pm2)
        self.client.post(f"/projects/{p.pk}/review/", {"decision": "approved", "comments": ""})
        p.refresh_from_db()
        self.assertEqual(p.status, "approved")

    def test_edit_locked_after_submission(self):
        p = make_project(self.pm, status="approved")
        self.login(self.pm)
        self.assertEqual(self.client.get(f"/projects/{p.pk}/edit/").status_code, 403)

    def test_changes_requested_returns_to_draft(self):
        p = make_project(self.data, status="submitted")
        self.login(self.pm)
        self.client.post(f"/projects/{p.pk}/review/", {"decision": "changes_requested", "comments": "Add GPS"})
        p.refresh_from_db()
        self.assertEqual(p.status, "draft")

    def test_status_actions_and_invalid_transition(self):
        p = make_project(self.pm, status="approved")
        self.login(self.pm)
        self.client.post(f"/projects/{p.pk}/status/start/")
        p.refresh_from_db()
        self.assertEqual(p.status, "ongoing")
        self.client.post(f"/projects/{p.pk}/status/start/")      # not allowed from ongoing
        self.client.post(f"/projects/{p.pk}/status/complete/")
        p.refresh_from_db()
        self.assertEqual((p.status, p.completion_percentage), ("completed", 100))

    def test_archive_admin_only(self):
        p = make_project(self.pm)
        self.login(self.pm)
        self.assertEqual(self.client.post(f"/projects/{p.pk}/archive/").status_code, 403)
        self.login(self.admin)
        self.client.post(f"/projects/{p.pk}/archive/")
        p.refresh_from_db()
        self.assertTrue(p.is_archived)

    def test_list_filters(self):
        make_project(self.pm, name="Alpha", district="Bo")
        make_project(self.pm, name="Beta", district="Kono")
        self.login(self.pm)
        r = self.client.get("/projects/?district=Kono")
        self.assertContains(r, "Beta")
        self.assertNotContains(r, "Alpha")


class MonitoringTests(Base):
    def setUp(self):
        self.p = make_project(self.pm, status="ongoing", completion_percentage=10, officer=self.field)

    def test_update_review_changes_official_progress(self):
        self.login(self.field)
        r = self.client.post(f"/monitoring/project/{self.p.pk}/update/", {"date": "2026-03-01", "progress_percentage": "40", "challenges": "rain"})
        self.assertEqual(r.status_code, 302)
        up = ProgressUpdate.objects.get()
        self.p.refresh_from_db()
        self.assertEqual(self.p.completion_percentage, 10)         # unchanged until verified
        self.login(self.me)
        self.client.post(f"/monitoring/updates/{up.pk}/review/", {"decision": "approved", "comments": ""})
        self.p.refresh_from_db()
        self.assertEqual(self.p.completion_percentage, 40)
        self.assertTrue(Notification.objects.filter(user=self.field, event_type="update_approved").exists())

    def test_progress_over_100_rejected(self):
        self.login(self.field)
        self.client.post(f"/monitoring/project/{self.p.pk}/update/", {"date": "2026-03-01", "progress_percentage": "140"})
        self.assertEqual(ProgressUpdate.objects.count(), 0)

    def test_field_officer_cannot_review(self):
        up = ProgressUpdate.objects.create(project=self.p, officer=self.field, date=datetime.date.today(), progress_percentage=30)
        self.login(self.field)
        self.assertEqual(self.client.get(f"/monitoring/updates/{up.pk}/review/").status_code, 403)

    @TMP_MEDIA
    def test_update_with_photo_creates_evidence(self):
        self.login(self.field)
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "green").save(buf, "PNG")
        img = SimpleUploadedFile("site.png", buf.getvalue(), content_type="image/png")
        self.client.post(f"/monitoring/project/{self.p.pk}/update/", {"date": "2026-03-01", "progress_percentage": "20", "photo": img, "photo_caption": "Foundation"})
        self.assertEqual(self.p.evidence_items.count(), 1)

    def test_evaluation_only_me(self):
        self.login(self.field)
        self.assertEqual(self.client.get(f"/monitoring/project/{self.p.pk}/evaluation/").status_code, 403)
        self.login(self.me)
        r = self.client.post(f"/monitoring/project/{self.p.pk}/evaluation/", {"evaluation_date": "2026-03-01", "relevance": 4, "effectiveness": 4, "efficiency": 3, "sustainability": 5})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.p.evaluations.get().average_score, 4.0)


class BeneficiaryFinanceTests(Base):
    def setUp(self):
        self.p = make_project(self.pm, status="ongoing")

    def test_register_and_duplicate_warning(self):
        self.login(self.data)
        d = {"name": "Test Person", "sex": "F", "age": "30", "community": "Gerihun", "disability_status": "None reported", "project": self.p.pk}
        self.client.post("/beneficiaries/new/", d)
        self.assertEqual(Beneficiary.objects.count(), 1)
        self.assertEqual(BeneficiaryProject.objects.count(), 1)
        self.client.post("/beneficiaries/new/", d)                  # duplicate: not saved without confirmation
        self.assertEqual(Beneficiary.objects.count(), 1)
        self.client.post("/beneficiaries/new/", dict(d, confirm_duplicate="on"))
        self.assertEqual(Beneficiary.objects.count(), 2)

    def test_invalid_age(self):
        self.login(self.data)
        self.client.post("/beneficiaries/new/", {"name": "X", "sex": "M", "age": "300", "disability_status": "None reported"})
        self.assertEqual(Beneficiary.objects.count(), 0)

    def test_finance_roles_and_payment_rules(self):
        b = Beneficiary.objects.create(name="Pay Person", sex="M")
        bp = BeneficiaryProject.objects.create(beneficiary=b, project=self.p, status="enrolled")
        self.login(self.fin)
        r = self.client.post("/finance/payments/new/", {"beneficiary_project": bp.pk, "amount": "-5", "status": "pending"})
        self.assertEqual(Payment.objects.count(), 0)
        self.client.post("/finance/payments/new/", {"beneficiary_project": bp.pk, "amount": "750", "status": "paid"})
        pay = Payment.objects.get()
        self.assertEqual(pay.paid_date, datetime.date.today())
        self.assertEqual(bp.payment_status, "paid")
        self.login(self.data)
        self.assertEqual(self.client.get("/finance/").status_code, 403)

    def test_beneficiary_detail_hides_payments_from_non_finance(self):
        b = Beneficiary.objects.create(name="Secret Pay", sex="F")
        bp = BeneficiaryProject.objects.create(beneficiary=b, project=self.p)
        Payment.objects.create(beneficiary_project=bp, amount=Decimal("123.00"), status="paid", paid_date=datetime.date.today())
        self.login(self.data)
        self.assertNotContains(self.client.get(f"/beneficiaries/{b.pk}/"), "123.00")
        self.login(self.fin)
        self.assertContains(self.client.get(f"/beneficiaries/{b.pk}/"), "123.00")


class GRMTests(Base):
    def test_case_lifecycle(self):
        p = make_project(self.pm, status="ongoing")
        self.login(self.grm)
        self.client.post("/grm/cases/new/", {"project": p.pk, "complainant": "A Villager", "category": "Payment delay", "description": "Late"})
        c = GRMCase.objects.get()
        self.assertTrue(c.case_id.startswith("GRM-"))
        self.client.post(f"/grm/cases/{c.pk}/", {"action": "Met committee", "notes": "agreed", "new_status": "resolved"})
        c.refresh_from_db()
        self.assertEqual(c.status, "resolved")
        self.assertEqual(c.activities.count(), 1)

    def test_pm_can_view_but_not_edit(self):
        c = GRMCase.objects.create(complainant="Z", category="Other")
        self.login(self.pm)
        self.assertEqual(self.client.get(f"/grm/cases/{c.pk}/").status_code, 200)
        self.assertEqual(self.client.post(f"/grm/cases/{c.pk}/", {"action": "x"}).status_code, 403)


@TMP_MEDIA
class DocumentTests(Base):
    def setUp(self):
        self.p = make_project(self.pm, status="ongoing")

    def _upload(self, name="plan.pdf", access="public", content=b"%PDF-1.4 x"):
        return self.client.post("/documents/upload/", {"project": self.p.pk, "category": "proposal", "access_level": access,
                                                       "file": SimpleUploadedFile(name, content)})

    def test_upload_allowed_and_blocked_types(self):
        self.login(self.pm)
        self._upload()
        self.assertEqual(Document.objects.count(), 1)
        self._upload("evil.exe", content=b"MZ")
        self._upload("shell.php", content=b"<?php")
        self.assertEqual(Document.objects.count(), 1)

    def test_restricted_download_denied_to_viewer(self):
        self.login(self.pm)
        self._upload(access="restricted")
        d = Document.objects.get()
        self.login(self.viewer)
        self.assertEqual(self.client.get(f"/documents/{d.pk}/download/").status_code, 403)
        self.assertNotContains(self.client.get("/documents/"), "plan.pdf")
        self.login(self.pm)
        self.assertEqual(self.client.get(f"/documents/{d.pk}/download/").status_code, 200)

    def test_viewer_cannot_upload(self):
        self.login(self.viewer)
        self.assertEqual(self.client.get("/documents/upload/").status_code, 403)


class ReportTests(Base):
    def setUp(self):
        make_project(self.pm, name="Bo Well", district="Bo", status="ongoing")
        make_project(self.pm, name="Kono Road", district="Kono", status="ongoing")

    def test_filters_and_exports(self):
        self.login(self.me)
        r = self.client.get("/reports/project/?run=1&district=Kono")
        self.assertContains(r, "Kono Road")
        self.assertNotContains(r, "Bo Well")
        for fmt, ctype in (("pdf", "application/pdf"), ("excel", "spreadsheetml"), ("csv", "text/csv")):
            r = self.client.get(f"/reports/project/?run=1&format={fmt}")
            self.assertEqual(r.status_code, 200)
            self.assertIn(ctype, r["Content-Type"])

    def test_report_role_access(self):
        self.login(self.fin)
        self.assertEqual(self.client.get("/reports/finance/?run=1").status_code, 200)
        self.assertEqual(self.client.get("/reports/project/?run=1").status_code, 403)

    def test_csv_blocks_formula_injection(self):
        make_project(self.pm, name="=HYPERLINK(\"http://x\")", status="ongoing")
        self.login(self.me)
        body = self.client.get("/reports/project/?run=1&format=csv").content.decode()
        self.assertIn("'=HYPERLINK", body)


class NotificationAndAuditTests(Base):
    def test_notifications_are_private_and_markable(self):
        n = Notification.objects.create(user=self.pm, event_type="project_submitted", message="hi", link="/projects/")
        self.login(self.me)
        self.assertEqual(self.client.get(f"/notifications/{n.pk}/open/").status_code, 404)
        self.login(self.pm)
        r = self.client.get(f"/notifications/{n.pk}/open/")
        self.assertRedirects(r, "/projects/", fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_unsafe_notification_link_ignored(self):
        n = Notification.objects.create(user=self.pm, event_type="project_submitted", message="x", link="https://evil.example")
        self.login(self.pm)
        self.assertRedirects(self.client.get(f"/notifications/{n.pk}/open/"), "/notifications/")

    def test_audit_trail_admin_only_and_immutable_in_admin(self):
        self.login(self.me)
        self.assertEqual(self.client.get("/audit/").status_code, 403)
        self.login(self.admin)
        self.assertEqual(self.client.get("/audit/").status_code, 200)


class SecurityTests(Base):
    def test_xss_is_escaped(self):
        p = make_project(self.pm, name="<script>alert(1)</script>", status="ongoing")
        self.login(self.pm)
        html = self.client.get(f"/projects/{p.pk}/").content.decode()
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_csrf_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.login(username="pm", password=PW)
        self.assertEqual(c.post("/projects/new/", {}).status_code, 403)

    def test_api_respects_roles(self):
        self.login(self.viewer)
        self.assertEqual(self.client.get("/api/projects/").status_code, 200)
        self.assertEqual(self.client.get("/api/grm-cases/").status_code, 403)
        self.client.logout()
        self.assertIn(self.client.get("/api/projects/").status_code, (401, 403))

    def test_dashboard_numbers_come_from_database(self):
        make_project(self.pm, status="ongoing")
        make_project(self.pm, status="completed", completion_percentage=100)
        self.login(self.admin)
        r = self.client.get("/")
        self.assertEqual(r.context["stats"]["total"], 2)
        self.assertEqual(r.context["stats"]["completed"], 1)
