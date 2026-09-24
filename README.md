# AI Ustaz — MVP кабинета учителя

Django + готовая админка **[Unfold](https://github.com/unfoldadmin/django-unfold)** + **Claude** для AI-генерации
+ **[HyperFrames](https://github.com/heygen-com/hyperframes)** (open source, HTML → MP4) для видео к урокам.

## Что умеет

| Раздел | Возможности |
|---|---|
| Классы / ученики / предметы | справочники, ученики редактируются прямо внутри класса |
| Уроки | кнопка **«AI: план урока»** генерирует цели, план по этапам с таймингом и тезисы; **«AI: тест по уроку»** создаёт задание с вопросами и ключом ответов; **«Видео (Hyperframes)»** рендерит MP4-объяснялку по тезисам, плеер прямо в карточке |
| Задания | кнопка **«AI: проверить все ответы»** ставит балл и пишет комментарий каждому ученику |
| Ответы учеников | массовая AI-проверка выбранных ответов |
| Дашборд | уроки, ученики, непроверенные работы, средний балл |

Языки уроков: русский, қазақша, English.

## Запуск

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # впишите ANTHROPIC_API_KEY (без него работает демо-режим)
python manage.py migrate
python manage.py seed_demo    # демо-данные + учитель admin / admin
python manage.py runserver
```

Откройте http://127.0.0.1:8000/admin/ и войдите как `admin` / `admin`.

## Видео (HyperFrames)

Нужны **Node.js 22+** и **FFmpeg**. Один раз:

```bash
npx hyperframes@0.8.70 browser ensure   # скачает headless Chrome
npx hyperframes@0.8.70 doctor           # проверит окружение
```

Потом кнопка «Видео (Hyperframes)» в карточке урока или из консоли:

```bash
python manage.py render_lesson 1                # рендер в media/videos/lesson-1.mp4
python manage.py render_lesson 1 --only-build   # только HTML-проект в media/videos/lesson-1/
```

Шаблон видео: `school/templates/hyperframes/lesson.html` (обычный HTML + GSAP). Собранный проект можно открыть
в редакторе HyperFrames Studio: `cd media/videos/lesson-1 && npx hyperframes@0.8.70 preview`.

## Структура

```
config/                     настройки Django, меню Unfold
school/models.py            Subject, Classroom, Student, Lesson, Assignment, Submission
school/admin.py             админка и кнопки AI / видео
school/ai.py                Claude: план урока, тест, проверка ответов (структурированный JSON)
school/video.py             сборка и рендер HyperFrames-проекта
school/templates/hyperframes/lesson.html   шаблон видео
```
