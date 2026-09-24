from django.db.models import Avg
from django.urls import reverse
from django.utils.html import format_html

from . import ai
from .models import Lesson, Student, Submission


def dashboard_callback(request, context):
    """Карточки на главной странице админки."""
    avg = Submission.objects.filter(score__isnull=False).aggregate(v=Avg("score"))["v"]
    context["kpi"] = [
        {"title": "Уроков", "value": Lesson.objects.count(), "icon": "menu_book"},
        {"title": "Учеников", "value": Student.objects.count(), "icon": "groups"},
        {"title": "Не проверено", "value": Submission.objects.filter(score__isnull=True).count(), "icon": "pending_actions"},
        {"title": "Средний балл", "value": f"{avg:.1f}" if avg is not None else "—", "icon": "grade"},
    ]
    context["ai_enabled"] = ai.is_enabled()
    upcoming = Lesson.objects.select_related("subject", "classroom").order_by("-created_at")[:5]
    context["upcoming"] = upcoming
    context["lessons_table"] = {
        "headers": ["Урок", "Класс", "Статус", "Видео"],
        "rows": [
            [
                format_html('<a class="text-primary-600" href="{}">{}</a>',
                            reverse("admin:school_lesson_change", args=[l.pk]), l.title),
                l.classroom.name,
                l.get_status_display(),
                "есть" if l.video else "—",
            ]
            for l in upcoming
        ],
    }
    return context
