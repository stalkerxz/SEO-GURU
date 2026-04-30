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

## Первый запуск
```bash
cp .env.example .env
docker compose up --build
```

После старта:
- Web: http://localhost:3000
- API health: http://localhost:4000/health
- MinIO Console: http://localhost:9001

Дальше:
1. Откройте http://localhost:3000
2. Заполните контекст анализа (цель, ниша, язык и т.д.)
3. Загрузите видео
4. Дождитесь завершения анализа и проверьте:
   - технические параметры;
   - превью кадров;
   - SEO-пакеты по платформам;
   - копирование SEO-пакета по кнопке.

## Smoke-check
```bash
scripts/smoke-check.sh
```
Проверяет:
- наличие ключевых переменных окружения в `.env`;
- `docker compose ps`;
- доступность API (`/health`);
- доступность web (`http://localhost:3000`).

## Частые проблемы
- **Web не открывается**
  - Проверьте `docker compose ps` и что `web` слушает `0.0.0.0:3000`.
  - Проверьте, что порт `3000` не занят на хосте.
- **API не отвечает**
  - Откройте `http://localhost:4000/health`.
  - Проверьте `DATABASE_URL`, `REDIS_URL`, MinIO env и логи `api`.
- **Worker не обрабатывает задачу**
  - Проверьте, что `worker` запущен и что `redis` healthy.
  - Проверьте логи `worker` на ошибки ffmpeg/доступа к storage.
- **Кадры не отображаются**
  - Убедитесь, что API endpoint `/api/frames/:jobId/:filename` отвечает.
  - Проверьте наличие кадров в MinIO bucket или локальном storage.
- **MinIO bucket не создан**
  - Проверьте `MINIO_*` переменные и логи `api` при старте.
  - API создаёт bucket автоматически в режиме `STORAGE_MODE=minio`.
- **npm build не проходит**
  - Выполните `npm install` в корне и повторите `npm run -w apps/api build` / `npm run -w apps/web build`.


## Команды
```bash
npm run dev:web
npm run dev:api
npm run build
npm run lint
```

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

## MVP ограничения
Не включены:
- оплата
- авторизация
- автопостинг
- интеграции YouTube/Instagram/TikTok
- сложная тренд-аналитика

## PR8 / UI refresh
- Полностью обновлён интерфейс `apps/web` в стиле минималистичного SaaS dashboard (mobile-first, карточная структура, улучшенная визуальная иерархия).
- Функциональность сервиса не изменялась: backend-логика, worker-логика и API-контракты сохранены.
- Улучшены UX-состояния загрузки/ожидания/ошибки/готовности и удобство копирования SEO-контента.

## PR10 / Video-angle aware mock SEO differentiation
- SEO-генерация стала `video-aware`: worker формирует `videoFingerprint` и `contentHints` на основе технических данных, имени файла, контекста и манифеста кадров.
- В `ai_input` добавлены `frameManifest`, `videoFingerprint`, `contentHints`, чтобы prompt-builder и mock SEO учитывали конкретный ролик, а не только user context.
- Mock SEO теперь строится от `videoAngle` (auto/event/horizontal/square/vertical/generic), чтобы разные видео с одинаковым user context получали разные SEO-пакеты.
- Frontend показывает `videoAngle` и `generationBasis` в блоке «Видео-подсказки», чтобы было видно источники различий (technical fingerprint, filename hints, user keywords, mixed context).
- Ограничение текущей версии: computer vision/распознавания объектов пока нет, поэтому выводы строятся только по technical fingerprint, filename hints, user keywords и platform score.

## PR11 / Readable mock SEO copy
- Mock SEO-тексты очищены от внутренних technical values: служебные ключи больше не попадают в заголовки, описания, комментарии и хештеги.
- Добавлены readable helper-функции для целей, ниш, videoAngle, resolutionClass и platform hints — SEO-копия стала человекочитаемой и готовой к публикации.
- Улучшен приоритет videoAngle для авто-контента: auto/drift/phonk и auto/cinematic определяются раньше generic vertical short.
- Добавлен subject detection (detectedModel, filename tokens, keywords), чтобы авто-ролики явно упоминали модель (например, BMW X3).
- Платформенные версии (YouTube Video, Shorts, Reels, TikTok) теперь отличаются по стилю и плотности текста.
- Backend/API контракт не менялся.
