from datetime import datetime, timezone
from django.http import JsonResponse
from .checkers.base import Status
from .checkers.database import DatabaseChecker


_CHECKERS = [
    DatabaseChecker(),
]


def healthcheck(request):
    results = [c.check() for c in _CHECKERS]

    worst = max(r.status for r in results)
    now = datetime.now(timezone.utc)

    payload = {
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": worst.value,
        "components": [r.to_dict() for r in results],
    }

    http_status = 503 if worst == Status.DOWN else 200
    return JsonResponse(payload, status=http_status)
