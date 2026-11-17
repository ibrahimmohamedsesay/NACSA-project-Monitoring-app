from django.core.paginator import Paginator
from django.db.models import Q

DISTRICTS = [
    "Western Area Urban", "Western Area Rural", "Bo", "Bombali", "Bonthe",
    "Falaba", "Kailahun", "Kambia", "Karene", "Kenema", "Koinadugu", "Kono",
    "Moyamba", "Port Loko", "Pujehun", "Tonkolili",
]
PROJECT_TYPES = [
    "Water and Sanitation", "Education", "Health", "Roads and Bridges",
    "Livelihoods", "Agriculture", "Social Safety Net", "Community Infrastructure",
]


def paginate(request, queryset, per_page=15):
    page = Paginator(queryset, per_page).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return page, params.urlencode()


def search_q(term, *fields):
    q = Q()
    for f in fields:
        q |= Q(**{f"{f}__icontains": term})
    return q


def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "")
