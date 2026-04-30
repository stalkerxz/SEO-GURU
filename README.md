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
