from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from . import ai, video
from .models import Assignment, Classroom, Lesson, Student, Subject, Submission

# --- Пользователи в стиле Unfold ---
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


# --- Справочники ---
@admin.register(Subject)
class SubjectAdmin(ModelAdmin):
    search_fields = ["name"]


class StudentInline(TabularInline):
    model = Student
    extra = 0
    tab = True


@admin.register(Classroom)
class ClassroomAdmin(ModelAdmin):
    list_display = ["name", "grade", "year", "students_count"]
    list_filter = ["grade", "year"]
    search_fields = ["name"]
    inlines = [StudentInline]

    @display(description="Учеников")
    def students_count(self, obj):
        return obj.students.count()


@admin.register(Student)
class StudentAdmin(ModelAdmin):
    list_display = ["full_name", "classroom", "email"]
    list_filter = ["classroom"]
    search_fields = ["full_name", "email"]
    autocomplete_fields = ["classroom"]


# --- Уроки ---
class AssignmentInline(TabularInline):
    model = Assignment
    extra = 0
    fields = ["title", "kind", "max_score", "due_date"]
    show_change_link = True
    tab = True


def _ai_error(request, e):
    messages.error(request, f"AI: {e}")


@admin.register(Lesson)
class LessonAdmin(ModelAdmin):
    list_display = ["title", "subject", "classroom", "date", "show_status", "has_video"]
    list_filter = ["status", "subject", "classroom", "language"]
    search_fields = ["title", "plan"]
    date_hierarchy = "date"
    autocomplete_fields = ["subject", "classroom"]
    readonly_fields = ["video_player", "video_status"]
    inlines = [AssignmentInline]
    actions_detail = ["ai_plan", "ai_quiz", "make_video"]
    actions = ["bulk_ai_plan", "bulk_make_video"]
    fieldsets = [
        (None, {"fields": ["title", ("subject", "classroom"), ("date", "duration_min", "language"), "status", "notes"]}),
        ("Содержание урока", {"fields": ["objectives", "plan", "key_points"], "classes": ["tab"]}),
        ("Видео", {"fields": ["video_status", "video_player", "video"], "classes": ["tab"]}),
    ]

    @display(description="Статус", label={"draft": "warning", "ready": "info", "done": "success"})
    def show_status(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Видео", boolean=True)
    def has_video(self, obj):
        return bool(obj.video)

    @display(description="Плеер")
    def video_player(self, obj):
        if not obj.video:
            return "—"
        return format_html('<video src="{}" controls style="max-width:640px;border-radius:8px"></video>', obj.video.url)

    def _back(self, object_id):
        return redirect(reverse("admin:school_lesson_change", args=[object_id]))

    # Кнопки на странице урока
    @action(description="AI: план урока", icon="auto_awesome")
    def ai_plan(self, request, object_id):
        lesson = Lesson.objects.get(pk=object_id)
        try:
            res = ai.generate_lesson_plan(lesson)
        except ai.AIError as e:
            _ai_error(request, e)
            return self._back(object_id)
        lesson.objectives, lesson.plan, lesson.key_points = res.objectives, res.plan, res.key_points
        lesson.status = Lesson.Status.READY
        lesson.save()
        messages.success(request, "План урока сгенерирован")
        return self._back(object_id)

    @action(description="AI: тест по уроку", icon="quiz")
    def ai_quiz(self, request, object_id):
        lesson = Lesson.objects.get(pk=object_id)
        try:
            q = ai.generate_quiz(lesson)
        except ai.AIError as e:
            _ai_error(request, e)
            return self._back(object_id)
        a = Assignment.objects.create(
            lesson=lesson, title=q.title, kind=Assignment.Kind.QUIZ, content=q.questions, answer_key=q.answer_key
        )
        messages.success(request, f"Создан тест «{a.title}»")
        return redirect(reverse("admin:school_assignment_change", args=[a.pk]))

    @action(description="Видео (Hyperframes)", icon="movie")
    def make_video(self, request, object_id):
        video.render_async(int(object_id))
        messages.info(request, "Видео рендерится в фоне — обновите страницу через 1–2 минуты")
        return self._back(object_id)

    # Массовые действия в списке
    @admin.action(description="AI: сгенерировать планы уроков")
    def bulk_ai_plan(self, request, queryset):
        done = 0
        for lesson in queryset:
            try:
                res = ai.generate_lesson_plan(lesson)
            except ai.AIError as e:
                _ai_error(request, e)
                break
            lesson.objectives, lesson.plan, lesson.key_points = res.objectives, res.plan, res.key_points
            lesson.status = Lesson.Status.READY
            lesson.save()
            done += 1
        messages.success(request, f"Планов сгенерировано: {done}")

    @admin.action(description="Сделать видео (Hyperframes)")
    def bulk_make_video(self, request, queryset):
        for lesson in queryset:
            video.render_async(lesson.pk)
        messages.info(request, f"Запущен рендер: {queryset.count()} видео")


# --- Задания и ответы ---
class SubmissionInline(TabularInline):
    model = Submission
    extra = 0
    fields = ["student", "score", "ai_checked", "submitted_at"]
    readonly_fields = ["submitted_at"]
    show_change_link = True
    tab = True


def _grade(submission):
    res = ai.grade_submission(submission)
    submission.score, submission.feedback, submission.ai_checked = res.score, res.feedback, True
    submission.save()


@admin.register(Assignment)
class AssignmentAdmin(ModelAdmin):
    list_display = ["title", "lesson", "kind", "max_score", "due_date", "submissions_count"]
    list_filter = ["kind", "lesson__subject", "lesson__classroom"]
    search_fields = ["title", "content"]
    autocomplete_fields = ["lesson"]
    inlines = [SubmissionInline]
    actions_detail = ["ai_check_all"]

    @display(description="Сдали")
    def submissions_count(self, obj):
        return obj.submissions.count()

    @action(description="AI: проверить все ответы", icon="grading")
    def ai_check_all(self, request, object_id):
        pending = Submission.objects.filter(assignment_id=object_id, ai_checked=False)
        done = 0
        for s in pending:
            try:
                _grade(s)
            except ai.AIError as e:
                _ai_error(request, e)
                break
            done += 1
        messages.success(request, f"Проверено ответов: {done}")
        return redirect(reverse("admin:school_assignment_change", args=[object_id]))


@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    list_display = ["student", "assignment", "score", "ai_checked", "submitted_at"]
    list_filter = ["ai_checked", "assignment__lesson__classroom", "assignment"]
    search_fields = ["student__full_name", "answer"]
    autocomplete_fields = ["student", "assignment"]
    actions = ["ai_check"]

    @admin.action(description="AI: проверить выбранные ответы")
    def ai_check(self, request, queryset):
        done = 0
        for s in queryset.select_related("assignment"):
            try:
                _grade(s)
            except ai.AIError as e:
                _ai_error(request, e)
                break
            done += 1
        messages.success(request, f"Проверено ответов: {done}")
