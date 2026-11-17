from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme

from core.utils import paginate
from .models import Notification


@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user)
    f = request.GET.get("filter", "")
    if f == "unread":
        qs = qs.filter(is_read=False)
    page, params = paginate(request, qs, 20)
    return render(request, "notifications/list.html", {"page": page, "params": params, "f": f, "page_title": "Notifications"})


@login_required
def notification_open(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read", "updated_at"])
    if n.link and url_has_allowed_host_and_scheme(n.link, {request.get_host()}):
        return redirect(n.link)
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")
