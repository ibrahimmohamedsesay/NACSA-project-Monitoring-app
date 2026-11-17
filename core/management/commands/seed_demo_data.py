"""Create FICTIONAL demo data so every screen has something to show.

All names, communities and amounts are invented for demonstration. Run:
    python manage.py seed_demo_data            # add demo data (idempotent)
    python manage.py seed_demo_data --reset    # wipe demo records first
"""
import datetime
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role
from audit.models import AuditLog
from beneficiaries.models import Beneficiary, BeneficiaryProject
from documents.models import Document
from finance.models import Payment
from grm.models import GRMActivity, GRMCase
from monitoring.models import MonitoringVisit, ProgressUpdate, ProjectEvaluation
from notifications.models import Notification
from projects.models import Project, ProjectActivity, ProjectApproval, ProjectMilestone
from results.models import ResultIndicator

User = get_user_model()
DEMO_PASSWORD = "Demo@12345"

USERS = [
    ("admin_demo", "Aminata", "Conteh", "administrator", "ICT", True),
    ("mgmt_demo", "Mohamed", "Bangura", "management", "Management"),
    ("me_demo", "Fatmata", "Sesay", "me_officer", "Monitoring & Evaluation"),
    ("pm_demo", "Ibrahim", "Kamara", "project_manager", "Programmes"),
    ("pm2_demo", "Hawa", "Turay", "project_manager", "Programmes"),
    ("field_demo", "Sorie", "Koroma", "field_officer", "Field Operations"),
    ("field2_demo", "Mariama", "Jalloh", "field_officer", "Field Operations"),
    ("finance_demo", "Alusine", "Mansaray", "finance_officer", "Finance"),
    ("grm_demo", "Isatu", "Bah", "grm_officer", "Grievance Redress"),
    ("data_demo", "Abdul", "Fofanah", "data_entry_officer", "Data Unit"),
    ("viewer_demo", "Zainab", "Kallon", "viewer", "Partners"),
]

PROJECTS = [
    ("Community Water Well Rehabilitation", "Water and Sanitation", "Bo", "Kakua", "Gerihun", 180000, "ongoing", 62, -200, 120),
    ("Primary School Classroom Block", "Education", "Kenema", "Nongowa", "Blama", 420000, "ongoing", 45, -260, 150),
    ("Feeder Road Maintenance", "Roads and Bridges", "Port Loko", "Maforki", "Lunsar", 650000, "at_risk", 38, -300, 30),
    ("Village Health Post Construction", "Health", "Kailahun", "Luawa", "Segbwema", 510000, "ongoing", 71, -240, 90),
    ("Women's Cassava Processing Centre", "Livelihoods", "Tonkolili", "Kholifa", "Magburaka", 240000, "completed", 100, -400, -30),
    ("Cash for Work: Drainage Clearing", "Social Safety Net", "Western Area Urban", "Freetown East", "Kissy", 150000, "ongoing", 55, -120, 60),
    ("Community Market Shed", "Community Infrastructure", "Bombali", "Makeni", "Makeni", 310000, "delayed", 34, -330, -20),
    ("Rice Seed Multiplication Scheme", "Agriculture", "Moyamba", "Bagruwa", "Moyamba", 195000, "ongoing", 48, -150, 100),
    ("Latrine and Handwashing Stations", "Water and Sanitation", "Kono", "Gbense", "Koidu", 125000, "planned", 0, 15, 180),
    ("Secondary School Library Renovation", "Education", "Kambia", "Magbema", "Kambia", 98000, "under_review", 0, 40, 200),
    ("Foot Bridge Construction", "Roads and Bridges", "Pujehun", "Panga Krim", "Zimmi", 275000, "submitted", 0, 60, 220),
    ("Youth Skills Training Hub", "Livelihoods", "Bonthe", "Sittia", "Mattru Jong", 160000, "draft", 0, 90, 260),
]
COMMUNITIES = ["Gerihun", "Blama", "Lunsar", "Segbwema", "Magburaka", "Kissy", "Makeni", "Moyamba", "Koidu", "Kambia", "Zimmi", "Mattru Jong"]
FN_F = ["Aminata", "Fatmata", "Mariama", "Isatu", "Hawa", "Kadiatu", "Zainab", "Mabinty", "Adama", "Jeneba", "Salamatu", "Haja"]
FN_M = ["Mohamed", "Ibrahim", "Abu", "Sorie", "Alusine", "Foday", "Santigie", "Joseph", "Samuel", "Musa", "Alie", "Brima"]
LN = ["Kamara", "Sesay", "Conteh", "Koroma", "Bangura", "Turay", "Jalloh", "Mansaray", "Kallon", "Fofanah", "Bah", "Sankoh", "Samura", "Lahai", "Kargbo"]


class Command(BaseCommand):
    help = "Create fictional demo data (users for every role, projects, monitoring, beneficiaries, payments, GRM...)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing records before seeding.")

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(2026)
        today = datetime.date.today()
        if opts["reset"]:
            for m in (Notification, Payment, GRMActivity, GRMCase, Document, ProjectEvaluation, ProgressUpdate, MonitoringVisit, ResultIndicator,
                      BeneficiaryProject, Beneficiary, ProjectApproval, ProjectMilestone, ProjectActivity, Project):
                m.objects.all().delete()
            AuditLog.objects.all().delete()
            User.objects.filter(username__endswith="_demo").delete()
        from accounts.apps import create_roles
        create_roles(None)
        users = {}
        for row in USERS:
            username, first, last, role, dept = row[:5]
            u, created = User.objects.get_or_create(username=username, defaults=dict(
                first_name=first, last_name=last, email=f"{username}@demo.nacsa.local", department=dept, role=Role.objects.get(name=role),
                phone_number="+23276" + str(random.randint(100000, 999999)), is_staff=len(row) > 5, is_superuser=len(row) > 5))
            if created:
                u.set_password(DEMO_PASSWORD)
                u.save()
            users[username] = u
        if Project.objects.exists():
            self.stdout.write(self.style.WARNING("Projects already exist; skipping project data (use --reset to rebuild)."))
            self._summary()
            return
        pm, pm2, fo, fo2, me = users["pm_demo"], users["pm2_demo"], users["field_demo"], users["field2_demo"], users["me_demo"]
        data_u, fin, grm_u = users["data_demo"], users["finance_demo"], users["grm_demo"]
        projects = []
        for i, (name, ptype, district, chiefdom, community, budget, status, prog, start_off, end_off) in enumerate(PROJECTS):
            start = today + datetime.timedelta(days=start_off)
            end = today + datetime.timedelta(days=end_off) if start_off < 0 and end_off < 0 else today + datetime.timedelta(days=end_off)
            if end <= start:
                end = start + datetime.timedelta(days=240)
            p = Project.objects.create(
                name=name, project_type=ptype, district=district, chiefdom=chiefdom, community=community, ward=str(100 + i),
                gps_coordinates=f"{7.5 + i * 0.12:.4f}, {-12.2 + i * 0.09:.4f}", budget=Decimal(budget), start_date=start, expected_completion_date=end,
                officer=(fo if i % 2 == 0 else fo2), implementing_organization="Demo Community Development Committee",
                target_beneficiaries=random.choice([80, 120, 200, 350, 500]), status=status, completion_percentage=prog,
                description=f"Demonstration project: {name.lower()} in {community}, {district}.", objectives="Improve access to services; strengthen community ownership; deliver within budget and schedule.",
                created_by=data_u if i % 2 else pm)
            projects.append(p)
            for a_i, a in enumerate(["Community mobilisation", "Procurement of materials", "Construction / delivery", "Quality inspection", "Handover"]):
                st = "completed" if prog >= (a_i + 1) * 20 else ("in_progress" if prog > a_i * 20 else "not_started")
                ProjectActivity.objects.create(project=p, name=a, status=st)
            for m_i, m in enumerate(["Site assessment complete", "Mid-term review", "Practical completion"]):
                ProjectMilestone.objects.create(project=p, title=m, target_date=start + (end - start) * (m_i + 1) // 3, status="completed" if prog >= (m_i + 1) * 33 else "planned")
            if status not in ("draft", "submitted"):
                ProjectApproval.objects.create(project=p, reviewed_by=pm2 if p.created_by == pm else pm, decision="approved" if status != "under_review" else "changes_requested",
                                               comments="Meets criteria; approved for implementation." if status != "under_review" else "")
        # monitoring
        for p in projects:
            if p.status in ("ongoing", "at_risk", "delayed", "completed"):
                officer = p.officer
                for k in range(3):
                    pct = max(5, int(p.completion_percentage * (k + 1) / 3))
                    d = today - datetime.timedelta(days=(3 - k) * 21)
                    ProgressUpdate.objects.create(project=p, officer=officer, date=d, progress_percentage=pct,
                                                  activities_completed="Site works and community labour completed for this period.", activities_remaining="Remaining finishing and inspection.",
                                                  challenges="Heavy rain slowed access." if p.status in ("at_risk", "delayed") else "", recommendations="Increase labour and pre-position materials.",
                                                  review_status="approved" if k < 2 else "pending_review", reviewed_by=me if k < 2 else None, review_comments="Verified against site photos." if k < 2 else "")
                MonitoringVisit.objects.create(project=p, officer=me, visit_date=today - datetime.timedelta(days=14), notes="Site visit: works observed, committee interviewed, no safeguard concerns.")
        for p in projects[:4] + [projects[4]]:
            ProjectEvaluation.objects.create(project=p, evaluator=me, evaluation_date=today - datetime.timedelta(days=10), relevance=random.randint(3, 5), effectiveness=random.randint(3, 5),
                                             efficiency=random.randint(2, 5), sustainability=random.randint(3, 5), findings="Works are of acceptable quality.", lessons_learned="Early community engagement reduced disputes.", recommendations="Plan maintenance fund.")
        # results
        for p in projects:
            if p.status in ("draft", "submitted", "under_review"):
                continue
            tgt = Decimal(p.target_beneficiaries)
            cur = (tgt * p.completion_percentage / 100).quantize(Decimal("1"))
            ResultIndicator.objects.create(project=p, name="Number of beneficiaries reached", indicator_type="output", baseline=0, target=tgt, current_value=cur, reporting_period=f"{today.year}",
                                           status="achieved" if p.completion_percentage == 100 else ("off_track" if p.status == "delayed" else ("at_risk" if p.status == "at_risk" else "on_track")))
            ResultIndicator.objects.create(project=p, name="Households reporting improved access to service", indicator_type="outcome", baseline=10, target=80, current_value=10 + int(70 * p.completion_percentage / 100),
                                           reporting_period=f"{today.year}", status="achieved" if p.completion_percentage == 100 else "on_track")
        # beneficiaries
        bens = []
        for i in range(90):
            f = i % 2 == 0
            b = Beneficiary.objects.create(name=f"{random.choice(FN_F if f else FN_M)} {random.choice(LN)}", sex="F" if f else "M", age=random.randint(19, 68),
                                           contact_number="+23277" + str(random.randint(100000, 999999)) if i % 9 else "", community=random.choice(COMMUNITIES),
                                           household_info=f"Household of {random.randint(2, 9)}", disability_status="Physical" if i % 17 == 0 else "None reported")
            bens.append(b)
        active = [p for p in projects if p.status in ("ongoing", "at_risk", "delayed", "completed", "planned")]
        for b in bens:
            for p in random.sample(active, k=random.choice([1, 1, 2])):
                if p.status == "planned":
                    st = "targeted"
                else:
                    st = random.choice(["targeted", "enrolled", "enrolled", "serviced"])
                bp, _ = BeneficiaryProject.objects.get_or_create(beneficiary=b, project=p, defaults={"status": st, "support_type": "Cash for work" if "Cash" in p.name else "Project services"})
                if st in ("enrolled", "serviced") and random.random() < 0.7:
                    ps = random.choice(["paid", "paid", "pending", "processing", "failed"])
                    Payment.objects.create(beneficiary_project=bp, amount=Decimal(random.choice([500, 750, 1000, 1500])), status=ps,
                                           paid_date=today - datetime.timedelta(days=random.randint(1, 60)) if ps == "paid" else None)
        # GRM
        cats = ["Beneficiary selection", "Payment delay", "Quality of works", "Staff conduct", "Exclusion / targeting", "Other"]
        for i in range(10):
            p = random.choice(active)
            c = GRMCase.objects.create(project=p, complainant=f"{random.choice(FN_F + FN_M)} {random.choice(LN)}", category=random.choice(cats),
                                       description="Community member raised a concern during a site visit.", status=["open", "under_review", "resolved", "closed"][i % 4], assigned_to=grm_u)
            GRMActivity.objects.create(case=c, action="Case registered", notes="Logged through the community feedback box.", created_by=grm_u)
            if c.status in ("resolved", "closed"):
                GRMActivity.objects.create(case=c, action="Resolved after meeting with committee", notes="Complainant satisfied.", created_by=grm_u)
        # documents (tiny generated text files)
        for p in projects[:6]:
            for cat, acc in (("proposal", "public"), ("budget", "restricted")):
                d = Document(project=p, category=cat, access_level=acc, uploaded_by=pm)
                d.file.save(f"{cat}_{p.project_id}.pdf", ContentFile(f"%PDF-1.4\n% DEMO {cat} for {p.project_id}\n".encode()), save=True)
        # notifications
        for u in (pm, me, users["mgmt_demo"], fo):
            Notification.objects.create(user=u, event_type="project_submitted", message="Demo notification: a project is waiting for your attention.", link="/projects/")
        AuditLog.objects.create(user=users["admin_demo"], action="seed", module="core", description="Demo data created")
        self._summary()

    def _summary(self):
        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready: {Project.objects.count()} projects, {Beneficiary.objects.count()} beneficiaries, "
            f"{Payment.objects.count()} payments, {GRMCase.objects.count()} grievances, {User.objects.count()} users."))
        self.stdout.write(f"Sign in with any *_demo username (admin_demo, pm_demo, me_demo, field_demo, finance_demo, grm_demo, data_demo, mgmt_demo, viewer_demo) and password: {DEMO_PASSWORD}")
