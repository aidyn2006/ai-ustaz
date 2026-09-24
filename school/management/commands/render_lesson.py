from django.core.management.base import BaseCommand

from school import video
from school.models import Lesson


class Command(BaseCommand):
    help = "Рендерит видео урока через HyperFrames (синхронно)"

    def add_arguments(self, parser):
        parser.add_argument("lesson_id", type=int)
        parser.add_argument("--only-build", action="store_true", help="Только собрать HTML-проект, без рендера")

    def handle(self, lesson_id, only_build, **opts):
        lesson = Lesson.objects.get(pk=lesson_id)
        if only_build:
            self.stdout.write(str(video.build_project(lesson)))
            return
        lesson.video.name = video.render(lesson)
        lesson.video_status = "Готово"
        lesson.save(update_fields=["video", "video_status"])
        self.stdout.write(self.style.SUCCESS(f"Готово: media/{lesson.video.name}"))
