import mimetypes
import os

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from audit.utils import log
from core.permissions import can, is_admin, module_required
from core.utils import paginate
from notifications.utils import notify, users_with_roles
from projects.models import Project
from .forms import DocumentForm, EvidenceForm
from .models import Document, Evidence


def _can_open_restricted(user):
    return is_admin(user) or can(user, "documents", "restricted")


@module_required("documents", "view")
def document_list(request):
    g = request.GET
    qs = Document.objects.select_related("project", "uploaded_by")
    if not _can_open_restricted(request.user):
        qs = qs.filter(access_level="public")
    if g.get("q"):
        qs = qs.filter(Q(project__project_id__icontains=g["q"]) | Q(project__name__icontains=g["q"]) | Q(file__icontains=g["q"]))
    if g.get("category"):
        qs = qs.filter(category=g["category"])
    if g.get("project"):
        qs = qs.filter(project_id=g["project"])
    if g.get("access"):
        qs = qs.filter(access_level=g["access"])
    page, params = paginate(request, qs)
    ev = Evidence.objects.select_related("project", "uploaded_by")[:12]
    return render(request, "documents/list.html", {
        "page": page, "params": params, "g": g, "page_title": "Documents & evidence", "evidence": ev,
        "categories": Document.CATEGORY_CHOICES, "projects": Project.objects.filter(documents__isnull=False).distinct()})


@module_required("documents", "add")
def document_upload(request):
    form = DocumentForm(request.POST or None, request.FILES or None, initial={"project": request.GET.get("project")})
    if request.method == "POST" and form.is_valid():
        d = form.save(commit=False)
        d.uploaded_by = request.user
        d.save()
        log(request.user, "upload", "documents", d.pk, f"Uploaded {d.get_category_display()} for {d.project.project_id} ({d.access_level})")
        notify(users_with_roles("project_manager", "me_officer"), "document_uploaded", f"New {d.get_category_display()} on {d.project.project_id}", reverse("projects:detail", args=[d.project_id]) + "?tab=documents")
        messages.success(request, "Document uploaded.")
        return redirect("documents:list")
    return render(request, "generic_form.html", {"form": form, "page_title": "Upload document", "cancel_url": "/documents/",
                                                  "subtitle": "Allowed: PDF, Word, Excel, JPG, PNG up to 25 MB. Restricted documents are visible only to authorised roles."})


@module_required("documents", "add")
def evidence_upload(request):
    form = EvidenceForm(request.POST or None, request.FILES or None, initial={"project": request.GET.get("project")})
    if request.method == "POST" and form.is_valid():
        e = form.save(commit=False)
        e.uploaded_by = request.user
        e.save()
        log(request.user, "upload", "documents", e.pk, f"Evidence photo ({e.phase}) for {e.project.project_id}")
        messages.success(request, "Evidence photo saved.")
        return redirect(reverse("projects:detail", args=[e.project_id]) + "?tab=documents")
    return render(request, "generic_form.html", {"form": form, "page_title": "Add evidence photo", "cancel_url": "/documents/"})


@module_required("documents", "view")
def document_download(request, pk):
    d = get_object_or_404(Document, pk=pk)
    if d.access_level == "restricted" and not _can_open_restricted(request.user):
        log(request.user, "denied", "documents", d.pk, "Attempted to open a restricted document")
        raise PermissionDenied
    if not d.file or not os.path.exists(d.file.path):
        raise Http404("File not found")
    log(request.user, "download", "documents", d.pk, f"Opened {os.path.basename(d.file.name)}")
    ctype = mimetypes.guess_type(d.file.name)[0] or "application/octet-stream"
    return FileResponse(open(d.file.path, "rb"), as_attachment=True, filename=os.path.basename(d.file.name), content_type=ctype)


@module_required("documents", "delete")
@require_POST
def document_delete(request, pk):
    d = get_object_or_404(Document, pk=pk)
    log(request.user, "delete", "documents", d.pk, f"Deleted document for {d.project.project_id}")
    d.file.delete(save=False)
    d.delete()
    messages.success(request, "Document deleted.")
    return redirect("documents:list")
