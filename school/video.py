"""Видео-объяснялки к урокам через HyperFrames (HTML -> MP4, open source, Apache-2.0).

Для каждого урока собирается HyperFrames-проект (index.html из шаблона
hyperframes/lesson.html) и рендерится командой `npx hyperframes render`.
Требуется Node.js 22+ и FFmpeg (`npx hyperframes doctor` покажет, чего не хватает).
"""

import json
import shutil
import subprocess
import threading
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

ASSETS = Path(__file__).resolve().parent / "hyperframes_assets"
INTRO, PER_POINT, OUTRO = 4, 4, 3

OUTRO_TEXT = {"ru": "Спасибо за внимание!", "kk": "Назар салғандарыңызға рахмет!", "en": "Thank you!"}


def project_dir(lesson) -> Path:
    return Path(settings.HYPERFRAMES_WORKDIR) / f"lesson-{lesson.pk}"


def build_project(lesson) -> Path:
    """Пишет HyperFrames-проект урока на диск и возвращает его папку."""
    points = [p for p in (lesson.key_points or []) if str(p).strip()] or [lesson.title]
    starts = [0] + [INTRO + i * PER_POINT for i in range(len(points))]
    outro_start = INTRO + len(points) * PER_POINT
    total = outro_start + OUTRO
    html = render_to_string(
        "hyperframes/lesson.html",
        {
            "lesson": lesson,
            "scenes": [{"start": s, "text": t} for s, t in zip(starts[1:], points)],
            "intro": INTRO,
            "per_point": PER_POINT,
            "outro": OUTRO,
            "outro_start": outro_start,
            "outro_text": OUTRO_TEXT.get(lesson.language, OUTRO_TEXT["ru"]),
            "total": total,
            "starts_json": json.dumps(starts + [outro_start, total]),
        },
    )
    d = project_dir(lesson)
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html, encoding="utf-8")
    shutil.copy(ASSETS / "gsap.min.js", d / "gsap.min.js")
    (d / "meta.json").write_text(json.dumps({"id": d.name, "name": d.name}), encoding="utf-8")
    return d


def render(lesson) -> str:
    """Синхронный рендер. Возвращает путь к mp4 относительно MEDIA_ROOT."""
    if not shutil.which("npx"):
        raise RuntimeError("npx не найден: установите Node.js 22+")
    d = build_project(lesson)
    rel = f"videos/lesson-{lesson.pk}.mp4"
    out = Path(settings.MEDIA_ROOT) / rel
    proc = subprocess.run(
        ["npx", "--yes", f"hyperframes@{settings.HYPERFRAMES_VERSION}", "render", str(d),
         "-o", str(out), "--quality", "draft", "--quiet"],
        capture_output=True, text=True, timeout=900,
    )
    if proc.returncode != 0 or not out.exists():
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-5:]
        raise RuntimeError("Ошибка рендера: " + " | ".join(tail))
    return rel


def render_async(lesson_id: int) -> None:
    """Рендер в фоне, чтобы не блокировать запрос в админке."""
    from .models import Lesson

    def job():
        lesson = Lesson.objects.get(pk=lesson_id)
        try:
            lesson.video.name = render(lesson)
            lesson.video_status = "Готово"
        except Exception as e:  # noqa: BLE001 — статус показываем учителю в админке
            lesson.video_status = str(e)[:200]
        lesson.save(update_fields=["video", "video_status"])

    Lesson.objects.filter(pk=lesson_id).update(video_status="Рендерится…")
    threading.Thread(target=job, daemon=True).start()
