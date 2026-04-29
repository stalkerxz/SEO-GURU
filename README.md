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
