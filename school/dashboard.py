from django.db.models import Avg

from . import ai
from .models import Lesson, Student, Submission


def dashboard_callback(request, context):
    """Карточки на главной странице админки."""
    avg = Submission.objects.filter(score__isnull=False).aggregate(v=Avg("score"))["v"]
    context["kpi"] = [
        {"title": "Уроков", "value": Lesson.objects.count()},
        {"title": "Учеников", "value": Student.objects.count()},
        {"title": "Не проверено", "value": Submission.objects.filter(score__isnull=True).count()},
        {"title": "Средний балл", "value": f"{avg:.1f}" if avg is not None else "—"},
    ]
    context["ai_enabled"] = ai.is_enabled()
    context["upcoming"] = Lesson.objects.select_related("subject", "classroom").order_by("-created_at")[:5]
    return context
