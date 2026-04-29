# video-seo-analyzer

Monorepo MVP для анализа видео (SEO-ready metadata) с веб-интерфейсом, API и Python worker.

## Стек
- `apps/web`: Next.js 14 + React + Tailwind
- `apps/api`: Node.js + Express + TypeScript
- `apps/worker`: Python background worker + FFmpeg
- PostgreSQL, Redis, MinIO
- Docker Compose

## Архитектура
1. Пользователь загружает видео на frontend.
2. Frontend отправляет файл на API (`/api/videos/upload`).
3. API сохраняет видео в MinIO (или локально в dev), создает задачу и кладет в Redis queue.
4. Worker забирает задачу, анализирует через `ffprobe`, извлекает ключевые кадры.
5. Worker обновляет задачу в PostgreSQL.
6. Frontend опрашивает API и отображает статус + результат.


## PR2: отчёт анализа и превью кадров
Добавлено:
- API эндпоинт `GET /api/frames/:jobId/:filename` для безопасной выдачи JPEG-превью кадров (local storage и MinIO proxy).
- API при старте ждёт готовности PostgreSQL, применяет idempotent-миграцию: `ALTER TABLE video_jobs ADD COLUMN IF NOT EXISTS analysis_report JSONB`, и в режиме MinIO проверяет/создаёт bucket с retry.
- Worker дополняет кадры полями `approxTimeSec` и `previewUrl`.
- В `video_jobs` добавлено поле `analysis_report` (JSONB), worker сохраняет базовый отчёт по технике, platform fit, issues, recommendations и SEO draft.
- Frontend показывает понятный отчёт: статус, технические параметры, сетку кадров, оценку платформ, проблемы, рекомендации, SEO-заготовку.
- Автоопрос статуса задачи каждые 2 секунды до завершения (`done`/`failed`).


## PR3: AI-ready SEO scaffolding (mock/offline)
Добавлено:
- Worker формирует `ai_input` внутри `analysis_report` (technicalSummary, frameSummary, platformFit, issues, recommendations, userGoal/niche/language).
- Добавлен `apps/worker/seo_prompt_builder.py` с функциями сборки AI-промптов на русском (`build_ai_video_analysis_prompt`, `build_platform_seo_prompt`).
- Добавлен `apps/worker/seo_mock_generator.py` с offline/mock-генерацией SEO-пакетов для YouTube Video, YouTube Shorts, Instagram Reels и TikTok.
- `seoDraft` теперь заполняется реальными mock-данными для всех платформ вместо пустых значений.
- Frontend показывает SEO-пакеты по платформам в удобных блоках и кнопки «Скопировать» для ключевых полей.

Важно:
- Внешние AI API (OpenAI/Gemini/Claude и др.) в PR3 не подключаются.
- SEO-генерация сейчас работает в mock/offline режиме.
- Следующий шаг после PR3 — заменить mock-генератор на реальный AI-провайдер.

## Быстрый старт
```bash
cp .env.example .env
docker compose up --build
```

После запуска:
- Web: http://localhost:3000
- API: http://localhost:4000
- MinIO Console: http://localhost:9001

## Локальная разработка без Docker
1) Скопировать окружение:
```bash
cp .env.example .env
```
2) Установить зависимости:
```bash
npm install
cd apps/worker && pip install -r requirements.txt
```
3) Запустить сервисы отдельно:
```bash
npm run dev:web
npm run dev:api
python apps/worker/worker.py  # background consumer
```

## Команды
```bash
npm run dev:web
npm run dev:api
npm run build
npm run lint
```

## MVP ограничения
Не включены:
- оплата
- авторизация
- автопостинг
- интеграции YouTube/Instagram/TikTok
- сложная тренд-аналитика

## PR4: реальный AI-провайдер с безопасным fallback
Добавлено:
- Worker получил AI service слой `apps/worker/ai_seo_service.py`.
- Добавлен переключатель провайдера через env: `AI_PROVIDER=mock|openai`.
- При `AI_PROVIDER=openai` и пустом `OPENAI_API_KEY` автоматически включается fallback на mock + warning.
- При ошибках OpenAI (включая ошибки JSON) выполняется fallback на mock (глобально или точечно по платформе), чтобы анализ не падал.
- В `analysis_report` добавлены поля: `aiProviderUsed`, `aiFallbackUsed`, `aiWarnings`.
- Frontend показывает строку `AI provider`, `Fallback`, а также warnings при наличии.

Настройки env:
- `AI_PROVIDER=mock`
- `OPENAI_API_KEY=`
- `OPENAI_MODEL=gpt-4.1-mini`
- `AI_TIMEOUT_SECONDS=60`

Как это работает:
- `AI_PROVIDER=mock`: всегда используется локальный mock-генератор.
- `AI_PROVIDER=openai`: используется OpenAI, но без ключа или при ошибках автоматически используется mock.
- API-ключи нельзя коммитить в репозиторий.


## PR5: User context for AI SEO
- Перед загрузкой видео пользователь задаёт цель, нишу, язык, гео, бренд/автора и ключевые слова.
- Контекст сохраняется в `video_jobs.user_context` и прокидывается в `analysis_report.ai_input`.
- Контекст влияет и на OpenAI SEO-генерацию, и на mock fallback SEO.

Run:
```bash
cp .env.example .env
docker compose up --build
```
