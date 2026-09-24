import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from school.models import Assignment, Classroom, Lesson, Student, Subject, Submission


class Command(BaseCommand):
    help = "Создаёт демо-данные и учителя admin/admin"

    def handle(self, *args, **opts):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "", os.getenv("ADMIN_PASSWORD", "admin"))
            self.stdout.write("Учитель: admin / admin")

        math, _ = Subject.objects.get_or_create(name="Математика")
        Subject.objects.get_or_create(name="Физика")
        Subject.objects.get_or_create(name="Қазақ тілі")
        c7, _ = Classroom.objects.get_or_create(name="7А", grade=7)
        names = ["Айдана Сейтқали", "Нурлан Ахметов", "Дана Ким", "Ерлан Омаров", "Аружан Бекова"]
        students = [Student.objects.get_or_create(full_name=n, classroom=c7)[0] for n in names]

        lesson, created = Lesson.objects.get_or_create(
            title="Линейные уравнения", subject=math, classroom=c7,
            defaults={
                "notes": "Больше примеров из жизни, работа в парах",
                "key_points": ["Что такое линейное уравнение", "ax + b = 0", "Переносим слагаемые", "Проверка корня"],
            },
        )
        if created:
            hw = Assignment.objects.create(
                lesson=lesson, title="Решите уравнение 3x + 6 = 0 и объясните шаги",
                kind=Assignment.Kind.HOMEWORK, content="Решите 3x + 6 = 0. Опишите каждый шаг.",
                answer_key="x = -2; перенос 6 вправо с минусом, деление на 3", max_score=5,
            )
            answers = ["3x = -6, x = -2", "x = 2", "Переносим 6: 3x = -6, делим на 3: x = -2. Проверка: 3·(-2)+6=0"]
            for s, a in zip(students, answers):
                Submission.objects.create(assignment=hw, student=s, answer=a)
        self.stdout.write(self.style.SUCCESS("Демо-данные готовы"))
