from django.db import models


class Subject(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Classroom(models.Model):
    name = models.CharField("Класс", max_length=20, help_text="Например: 7А")
    grade = models.PositiveSmallIntegerField("Параллель", default=7)
    year = models.CharField("Учебный год", max_length=9, default="2026-2027")

    class Meta:
        verbose_name = "Класс"
        verbose_name_plural = "Классы"
        ordering = ["grade", "name"]

    def __str__(self):
        return self.name


class Student(models.Model):
    full_name = models.CharField("ФИО", max_length=150)
    classroom = models.ForeignKey(
        Classroom, verbose_name="Класс", on_delete=models.CASCADE, related_name="students"
    )
    email = models.EmailField("Email", blank=True)

    class Meta:
        verbose_name = "Ученик"
        verbose_name_plural = "Ученики"
        ordering = ["classroom", "full_name"]

    def __str__(self):
        return self.full_name


class Lesson(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        READY = "ready", "Готов"
        DONE = "done", "Проведён"

    class Language(models.TextChoices):
        RU = "ru", "Русский"
        KK = "kk", "Қазақша"
        EN = "en", "English"

    title = models.CharField("Тема урока", max_length=200)
    subject = models.ForeignKey(Subject, verbose_name="Предмет", on_delete=models.PROTECT)
    classroom = models.ForeignKey(Classroom, verbose_name="Класс", on_delete=models.CASCADE)
    date = models.DateField("Дата", null=True, blank=True)
    duration_min = models.PositiveSmallIntegerField("Длительность, мин", default=45)
    language = models.CharField("Язык", max_length=2, choices=Language, default=Language.RU)
    notes = models.TextField("Пожелания для AI", blank=True, help_text="Что учесть при генерации")
    objectives = models.TextField("Цели урока", blank=True)
    plan = models.TextField("План урока", blank=True)
    key_points = models.JSONField("Ключевые тезисы (для видео)", default=list, blank=True)
    status = models.CharField("Статус", max_length=10, choices=Status, default=Status.DRAFT)
    video = models.FileField("Видео (Hyperframes)", upload_to="videos/", blank=True)
    video_status = models.CharField("Статус видео", max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.subject} · {self.classroom} · {self.title}"


class Assignment(models.Model):
    class Kind(models.TextChoices):
        QUIZ = "quiz", "Тест"
        HOMEWORK = "homework", "Домашнее задание"
        ESSAY = "essay", "Эссе"

    lesson = models.ForeignKey(
        Lesson, verbose_name="Урок", on_delete=models.CASCADE, related_name="assignments"
    )
    title = models.CharField("Название", max_length=200)
    kind = models.CharField("Тип", max_length=10, choices=Kind, default=Kind.QUIZ)
    content = models.TextField("Условие / вопросы")
    answer_key = models.TextField("Ответы / критерии", blank=True)
    max_score = models.PositiveSmallIntegerField("Макс. балл", default=10)
    due_date = models.DateField("Срок сдачи", null=True, blank=True)

    class Meta:
        verbose_name = "Задание"
        verbose_name_plural = "Задания"

    def __str__(self):
        return self.title


class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment, verbose_name="Задание", on_delete=models.CASCADE, related_name="submissions"
    )
    student = models.ForeignKey(Student, verbose_name="Ученик", on_delete=models.CASCADE)
    answer = models.TextField("Ответ ученика")
    score = models.PositiveSmallIntegerField("Балл", null=True, blank=True)
    feedback = models.TextField("Комментарий", blank=True)
    ai_checked = models.BooleanField("Проверено AI", default=False)
    submitted_at = models.DateTimeField("Сдано", auto_now_add=True)

    class Meta:
        verbose_name = "Ответ ученика"
        verbose_name_plural = "Ответы учеников"
        unique_together = [("assignment", "student")]

    def __str__(self):
        return f"{self.student} → {self.assignment}"
