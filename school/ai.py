"""AI-помощник учителя на Claude (Anthropic SDK).

Если ключ ANTHROPIC_API_KEY не задан, работает демо-режим с заглушками,
чтобы MVP можно было прокликать без ключа.
"""

import os

import anthropic
from django.conf import settings
from pydantic import BaseModel

LANG_NAMES = {"ru": "русском", "kk": "казахском", "en": "английском"}

SYSTEM = (
    "Ты — опытный методист и помощник школьного учителя в Казахстане. "
    "Пиши конкретно, по делу, с учётом возраста учеников и обновлённой программы МОН РК."
)


class LessonPlan(BaseModel):
    objectives: str
    plan: str
    key_points: list[str]


class Quiz(BaseModel):
    title: str
    questions: str
    answer_key: str


class Grading(BaseModel):
    score: int
    feedback: str


class AIError(Exception):
    pass


def is_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def _ask(prompt: str, schema: type[BaseModel]) -> BaseModel:
    client = anthropic.Anthropic()
    try:
        response = client.messages.parse(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
    except anthropic.APIConnectionError as e:
        raise AIError(f"Нет соединения с Claude API: {e}") from e
    except anthropic.RateLimitError as e:
        raise AIError("Превышен лимит запросов к Claude, попробуйте позже") from e
    except anthropic.APIStatusError as e:
        raise AIError(f"Ошибка Claude API ({e.status_code}): {e.message}") from e
    if response.stop_reason == "refusal":
        raise AIError("Claude отказался выполнять запрос")
    if response.parsed_output is None:
        raise AIError(f"Не удалось разобрать ответ (stop_reason={response.stop_reason})")
    return response.parsed_output


def _lesson_context(lesson) -> str:
    return (
        f"Предмет: {lesson.subject}. Класс: {lesson.classroom} ({lesson.classroom.grade} класс). "
        f"Тема: «{lesson.title}». Длительность: {lesson.duration_min} минут. "
        f"Язык ответа: на {LANG_NAMES.get(lesson.language, 'русском')} языке."
        + (f"\nПожелания учителя: {lesson.notes}" if lesson.notes else "")
    )


def generate_lesson_plan(lesson) -> LessonPlan:
    if not is_enabled():
        return LessonPlan(
            objectives=f"[демо] Ученики поймут основные понятия темы «{lesson.title}».",
            plan=(
                "1. Организационный момент (3 мин)\n"
                "2. Актуализация знаний (7 мин)\n"
                f"3. Новая тема: {lesson.title} (15 мин)\n"
                "4. Практика в парах (12 мин)\n"
                "5. Рефлексия и домашнее задание (8 мин)"
            ),
            key_points=[lesson.title, "Ключевое понятие", "Пример из жизни", "Итог урока"],
        )
    return _ask(
        _lesson_context(lesson)
        + "\n\nСоставь план урока по этапам с таймингом (поле plan), цели урока по SMART "
        "(поле objectives) и 3–5 коротких тезисов до 8 слов каждый для слайдов "
        "обучающего видео (поле key_points).",
        LessonPlan,
    )


def generate_quiz(lesson, count: int = 5) -> Quiz:
    if not is_enabled():
        questions = "\n".join(
            f"{i}. [демо] Вопрос {i} по теме «{lesson.title}»?\n   a) … b) … c) … d) …"
            for i in range(1, count + 1)
        )
        return Quiz(
            title=f"Тест: {lesson.title}",
            questions=questions,
            answer_key=", ".join(f"{i}-a" for i in range(1, count + 1)),
        )
    return _ask(
        _lesson_context(lesson)
        + (f"\nПлан урока:\n{lesson.plan}" if lesson.plan else "")
        + f"\n\nСоставь тест из {count} вопросов с 4 вариантами ответа (поле questions), "
        "ключ ответов в формате «1-b, 2-a…» (поле answer_key) и название теста (поле title).",
        Quiz,
    )


def grade_submission(submission) -> Grading:
    a = submission.assignment
    if not is_enabled():
        return Grading(
            score=round(a.max_score * 0.8),
            feedback="[демо] Хорошая работа. Добавьте больше примеров и проверьте выводы.",
        )
    result = _ask(
        f"Задание ({a.get_kind_display()}): {a.title}\n{a.content}\n\n"
        f"Ответы / критерии: {a.answer_key or 'не заданы, оцени по существу'}\n"
        f"Максимальный балл: {a.max_score}\n\n"
        f"Ответ ученика:\n{submission.answer}\n\n"
        "Оцени ответ (поле score, целое от 0 до максимума) и дай ученику короткий "
        "доброжелательный комментарий: что хорошо и что улучшить (поле feedback).",
        Grading,
    )
    result.score = max(0, min(result.score, a.max_score))
    return result
