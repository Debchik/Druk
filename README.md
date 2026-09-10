# Друк — внутренняя платформа команды

Закрытое рабочее пространство для двух сооснователей: задачи, программы и заявки, база ответов, приватные файлы, встречи/решения и read-only GitHub Issues.

Ветка для платформы: `internal-platform`. Существующий лендинг в `main` намеренно не заменяется до отдельного запуска GitHub Pages workflow.

## Архитектура

```text
GitHub Pages: React + TypeScript + Vite + HashRouter
        │
        ├── Supabase Auth (email/password, без публичной регистрации)
        │
        └── Authorization: Bearer <user JWT>
                      │
                      ▼
                 FastAPI
                   ├── проверяет JWT через Supabase Auth /auth/v1/user
                   ├── проверяет workspace membership
                   ├── PostgREST с тем же user JWT → PostgreSQL + RLS
                   ├── приватный Supabase Storage
                   └── GitHub REST API (server-side token)
```

Service role не используется в обычном backend CRUD. Он нужен только для одноразового bootstrap workspace, если используется `scripts/bootstrap_workspace.py` или соответствующий manual workflow.

## Что реализовано

- Supabase Auth + закрытый workspace для двух участников;
- RLS для бизнес-таблиц и Storage;
- dashboard: проект, быстрые ссылки, недельный фокус, задачи, дедлайны, последние решения;
- задачи с ответственным, статусом, неделей, дедлайном и блокировкой;
- программы, чек-листы, статусы, архив;
- общая база ответов + поиск по вопросу/ответу/keywords;
- независимое копирование ответа из библиотеки в заявку;
- immutable snapshot отправленной заявки;
- приватные общие файлы и документы программы;
- актуальная презентация как file ID + временный signed URL;
- встречи и решения;
- GitHub Issues read-only: pagination, PR exclusion, cache, stale/error state, cooldown;
- versioned JSON export;
- Storage backup script;
- FastAPI Dockerfile + Render Blueprint;
- GitHub Actions: CI, Supabase bootstrap, Render deploy hook, GitHub Pages deployment.

Не реализованы намеренно: LLM/AI, semantic search, transcription, GitHub Projects, двусторонняя GitHub sync, billing, realtime collaborative editing.

## Структура

```text
frontend/                 React + TypeScript + Vite
backend/                  FastAPI
supabase/migrations/      schema + RLS + private Storage policies
scripts/                  bootstrap + Storage export
.github/workflows/        CI / bootstrap / Pages / Render hook
render.yaml               Render Blueprint
```

## 1. Supabase

### 1.1 Создать проект и пользователей

Создайте Supabase project. В Authentication создайте два email/password аккаунта вручную. Публичной регистрации в UI приложения нет.

### 1.2 Применить миграцию

На чистом проекте выполните:

```text
supabase/migrations/001_init.sql
```

Она создаёт таблицы, индексы, ограничения, search RPC, private bucket `workspace-files`, RLS policies и Storage policies.

### 1.3 Добавить двух сооснователей

Есть два варианта.

**A. Через GitHub Actions:** добавьте Repository Secrets `SUPABASE_URL` и `SUPABASE_SERVICE_ROLE_KEY`, затем на ветке `internal-platform` вручную запустите workflow `Bootstrap Supabase workspace` и передайте два UUID как inputs. UUID не нужно коммитить.

**B. Локально:**

```bash
export SUPABASE_URL=...
export SUPABASE_SERVICE_ROLE_KEY=...
export BOOTSTRAP_USER_IDS=<uuid1>,<uuid2>
export BOOTSTRAP_DISPLAY_NAMES='Имя 1,Имя 2'
python scripts/bootstrap_workspace.py
```

Реальные UUID и service role key не должны попадать в git.

## 2. Backend локально

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Health: `GET /health`. OpenAPI: `/docs` в development.

### Backend env

| Переменная | Секрет | Назначение |
|---|---:|---|
| `ENVIRONMENT` | нет | `development` / `production` |
| `SUPABASE_URL` | нет | URL Supabase project |
| `SUPABASE_ANON_KEY` | нет* | publishable/anon key, сам по себе не даёт доступа |
| `SUPABASE_STORAGE_BUCKET` | нет | обычно `workspace-files` |
| `GITHUB_TOKEN` | да | fine-grained token только на чтение нужных репозиториев/Issues |
| `CORS_ORIGINS` | нет | точные origins через запятую |
| `MAX_FILE_SIZE_MIB` | нет | default `20` |
| `GITHUB_SYNC_COOLDOWN_SECONDS` | нет | default `30` |

`SUPABASE_SERVICE_ROLE_KEY` не нужен работающему backend.

## 3. Frontend локально

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Frontend variables

| Переменная | Назначение |
|---|---|
| `VITE_SUPABASE_URL` | публичный Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | публичный publishable/anon key |
| `VITE_API_URL` | URL FastAPI с `/api/v1`, например `https://...onrender.com/api/v1` |
| `VITE_BASE_PATH` | `/Druk/` для project Pages |

Никакие server-side secrets не должны начинаться с `VITE_`.

## 4. GitHub Secrets/Variables, которые нужны для публикации

### Repository → Settings → Secrets and variables → Actions → Variables

```text
VITE_SUPABASE_URL
VITE_SUPABASE_ANON_KEY
VITE_API_URL
```

Это значения, которые попадут в публичный frontend bundle; секретами они не считаются.

### Repository → Settings → Secrets and variables → Actions → Secrets

Для одноразового bootstrap через workflow:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Опционально, если Render service уже создан и нужно запускать его deploy из GitHub:

```text
RENDER_DEPLOY_HOOK_URL
```

Не кладите в обычные GitHub Variables: database password, service role, GitHub fine-grained token.

## 5. Backend на Render

`render.yaml` описывает Docker Web Service из ветки `internal-platform`.

В Render runtime environment задайте:

```text
ENVIRONMENT=production
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_STORAGE_BUCKET=workspace-files
GITHUB_TOKEN=...
CORS_ORIGINS=https://<github-login>.github.io
MAX_FILE_SIZE_MIB=20
GITHUB_SYNC_COOLDOWN_SECONDS=30
```

Render должен собирать `backend/Dockerfile`. Health check: `/health`. Backend слушает `0.0.0.0:${PORT}`.

После создания сервиса возьмите URL вида `https://<service>.onrender.com/api/v1` и сохраните его как GitHub Actions Variable `VITE_API_URL`.

Если создан Deploy Hook, его URL можно сохранить как Repository Secret `RENDER_DEPLOY_HOOK_URL` и использовать workflow `Trigger Render backend deploy`.

## 6. GitHub Pages

Frontend использует `HashRouter`, поэтому deep links работают как:

```text
https://<login>.github.io/Druk/#/programs/<id>
```

Публикация намеренно только ручная: workflow `Deploy internal platform to Pages` запускается с ветки `internal-platform` после заполнения `VITE_*` variables и готовности backend.

Важно: GitHub Pages для репозитория один. Запуск этого workflow заменит текущую Pages-публикацию лендинга этого репозитория. Код лендинга остаётся в `main`, но публичный Pages artifact будет платформой, пока не выполнен другой deploy.

## 7. GitHub Issues

Backend использует только `GITHUB_TOKEN`. Рекомендуется fine-grained token с минимальным доступом к выбранным repositories и read-only Issues/metadata.

Пользователь добавляет `owner/repository` в Settings платформы. Токен никогда не попадает в браузер.

## 8. Файлы

Поддерживаются PDF, PPT/PPTX, DOC/DOCX, XLS/XLSX, TXT, CSV, PNG, JPEG, WebP. Default limit 20 MiB.

Путь Storage содержит `workspace_id` и случайный UUID. Исходное имя хранится только в metadata. Bucket приватный. Signed URLs живут 5 минут.

Антивирус не реализован. Backend проверяет размер, расширение и базовую сигнатуру поддерживаемых форматов; HTML/SVG/archives не принимаются.

## 9. Экспорт и backup

UI экспортирует JSON с данными workspace и метаданными файлов, но не бинарники.

Для бинарников:

```bash
export SUPABASE_URL=...
export SUPABASE_ANON_KEY=...
export USER_ACCESS_TOKEN=...
export WORKSPACE_ID=...
python scripts/export_storage.py
```

Получается каталог файлов + `manifest.json`.

## 10. Проверки

Backend локально:

```bash
SUPABASE_URL=https://example.supabase.co \
SUPABASE_ANON_KEY=ci-placeholder-key-xxxxxxxxxxxx \
PYTHONPATH=backend pytest backend/tests -q -m 'not integration'
```

RLS integration test запускается отдельно только против test Supabase project.

Frontend CI выполняет `npm install`, lint, typecheck, Vitest и production build. В текущем рабочем окружении npm registry может быть недоступен, поэтому окончательная frontend-проверка выполняется в GitHub Actions после push.

## 11. Порядок production setup

1. Код в `internal-platform`.
2. Создать Supabase project и два Auth users.
3. Применить `001_init.sql`.
4. Bootstrap двух UUID.
5. Создать Render service из `internal-platform` и заполнить backend env.
6. Проверить `/health`.
7. Добавить `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL` в GitHub Actions Variables.
8. В Supabase Auth добавить production GitHub Pages URL в Site URL / Redirect URLs, если это требуется конфигурацией Auth.
9. Запустить `Deploy internal platform to Pages` с ветки `internal-platform`.
10. Войти обоими аккаунтами и проверить доступ, RLS, файлы, задачу и программу.

## Статус публикации исходников

Ветка `internal-platform` проходит обязательный GitHub Actions CI на каждый push: backend compile/tests и frontend lint/typecheck/tests/production build. Публичный Pages deploy запускается отдельно только после настройки Supabase и backend URL.
