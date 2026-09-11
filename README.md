# Друк — внутренняя платформа команды

Закрытое рабочее пространство для двух сооснователей: задачи, программы и заявки, база ответов, приватные файлы, встречи/решения и read-only GitHub Issues.

Ветка платформы: `internal-platform`. Лендинг в `main` не заменяется до отдельного ручного GitHub Pages deploy.

## Supabase: только новые API keys

Проект использует новую схему Supabase API keys и не требует legacy `anon` / `service_role` ключей:

- `sb_publishable_...` — публичный ключ приложения. Используется во frontend и backend как `apikey`; доступ пользователя по-прежнему ограничивается RLS.
- `sb_secret_...` — административный ключ. Используется только для одноразового bootstrap workspace и никогда не попадает во frontend или обычный backend runtime.
- User JWT после входа передаётся отдельно как `Authorization: Bearer <user-jwt>`.

Новые API keys являются opaque strings, а не JWT. Поэтому `sb_secret_...` не отправляется как `Authorization: Bearer ...`; bootstrap передаёт его только в заголовке `apikey`.

Backend сам не декодирует и не подписывает пользовательские JWT: он проверяет сессию через Supabase Auth `/auth/v1/user`. Поэтому приложение не зависит от legacy JWT secret и совместимо с новыми asymmetric JWT signing keys Supabase.

## Архитектура

```text
GitHub Pages: React + TypeScript + Vite + HashRouter
        │
        ├── Supabase Auth + sb_publishable_...
        │
        └── Authorization: Bearer <user JWT>
                      │
                      ▼
                 FastAPI
                   ├── /auth/v1/user: проверка пользовательской сессии
                   ├── workspace membership
                   ├── PostgREST: publishable apikey + user JWT → RLS
                   ├── private Supabase Storage
                   └── GitHub REST API (server-side token)
```

## Что реализовано

- Supabase Auth + закрытый workspace для двух участников;
- RLS для бизнес-таблиц и Storage;
- dashboard, задачи, дедлайны и недельный фокус;
- программы, чек-листы, статусы, архив и submission snapshots;
- база ответов и копирование ответов в заявку;
- приватные общие файлы и документы программ;
- встречи и решения;
- GitHub Issues read-only с pagination/cache/stale state;
- JSON export + Storage backup script;
- FastAPI Dockerfile + Render Blueprint;
- GitHub Actions: CI, Supabase bootstrap, Render hook, GitHub Pages deploy.

## 1. Supabase setup

### 1.1 Пользователи

В Supabase Authentication вручную создайте два email/password аккаунта. Публичной регистрации в UI нет.

### 1.2 Миграция

На чистом Supabase project примените:

```text
supabase/migrations/001_init.sql
```

Она создаёт таблицы, индексы, ограничения, search RPC, private bucket `workspace-files`, RLS и Storage policies.

### 1.3 Bootstrap двух сооснователей

В GitHub Repository Settings добавьте:

**Actions Variable**

```text
VITE_SUPABASE_URL
```

**Actions Secret**

```text
SUPABASE_SECRET_KEY=sb_secret_...
```

После этого вручную запустите workflow `Bootstrap Supabase workspace` из ветки `internal-platform` и передайте UUID двух Auth users. UUID не коммитятся.

Локальный вариант:

```bash
export SUPABASE_URL=https://YOUR_PROJECT.supabase.co
export SUPABASE_SECRET_KEY=sb_secret_...
export BOOTSTRAP_USER_IDS=<uuid1>,<uuid2>
export BOOTSTRAP_DISPLAY_NAMES='Имя 1,Имя 2'
python scripts/bootstrap_workspace.py
```

## 2. Backend

Локально:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Runtime env:

| Переменная | Секрет | Назначение |
|---|---:|---|
| `ENVIRONMENT` | нет | `development` / `production` |
| `SUPABASE_URL` | нет | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | нет | новый `sb_publishable_...` key |
| `SUPABASE_STORAGE_BUCKET` | нет | обычно `workspace-files` |
| `GITHUB_TOKEN` | да | fine-grained token с read-only доступом к нужным Issues |
| `CORS_ORIGINS` | нет | разрешённые frontend origins через запятую |
| `MAX_FILE_SIZE_MIB` | нет | default `20` |
| `GITHUB_SYNC_COOLDOWN_SECONDS` | нет | default `30` |

`SUPABASE_SECRET_KEY` работающему backend не нужен. CRUD выполняется от имени вошедшего пользователя, чтобы RLS оставался реальной границей безопасности.

## 3. Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

Frontend env:

```text
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
VITE_API_URL=http://localhost:8000/api/v1
VITE_BASE_PATH=/
```

Frontend валидирует, что передан именно ключ с префиксом `sb_publishable_`. Никакой `sb_secret_...` не должен иметь префикс `VITE_`.

## 4. GitHub Actions configuration

### Variables

```text
VITE_SUPABASE_URL
VITE_SUPABASE_PUBLISHABLE_KEY
VITE_API_URL
```

`VITE_API_URL` появится после публикации backend.

### Secrets

```text
SUPABASE_SECRET_KEY
```

Опционально:

```text
RENDER_DEPLOY_HOOK_URL
```

Legacy variables `VITE_SUPABASE_ANON_KEY`, `SUPABASE_ANON_KEY` и `SUPABASE_SERVICE_ROLE_KEY` больше нигде не используются.

## 5. Render backend

`render.yaml` описывает Docker Web Service из `internal-platform`.

В Render задайте:

```text
ENVIRONMENT=production
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_STORAGE_BUCKET=workspace-files
GITHUB_TOKEN=...
CORS_ORIGINS=https://<github-login>.github.io
MAX_FILE_SIZE_MIB=20
GITHUB_SYNC_COOLDOWN_SECONDS=30
```

Secret key в Render не нужен.

После создания сервиса сохраните URL вида `https://<service>.onrender.com/api/v1` как GitHub Actions Variable `VITE_API_URL`.

## 6. GitHub Pages

Frontend использует `HashRouter`, поэтому deep links имеют вид:

```text
https://<login>.github.io/Druk/#/programs/<id>
```

Workflow `Deploy internal platform to Pages` запускается вручную из `internal-platform`. Он требует `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` и `VITE_API_URL`.

GitHub Pages для репозитория один: такой deploy заменит текущий Pages artifact лендинга, хотя код лендинга останется в `main`.

## 7. Backup

Для бинарников Storage:

```bash
export SUPABASE_URL=...
export SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
export USER_ACCESS_TOKEN=...
export WORKSPACE_ID=...
python scripts/export_storage.py
```

## 8. Проверки

Backend CI:

```bash
SUPABASE_URL=https://example.supabase.co \
SUPABASE_PUBLISHABLE_KEY=sb_publishable_ci_placeholder_0123456789 \
PYTHONPATH=backend pytest backend/tests -q -m 'not integration'
```

Frontend CI выполняет `npm ci`, ESLint, TypeScript typecheck, Vitest и production build. На каждый push в `internal-platform` оба CI job должны быть зелёными.

Отдельный RLS integration test ожидает `RLS_SUPABASE_URL`, `RLS_SUPABASE_PUBLISHABLE_KEY`, `RLS_NON_MEMBER_TOKEN`, `RLS_WORKSPACE_ID`.

## 9. Production sequence

1. Создать Supabase project и двух Auth users.
2. Применить `supabase/migrations/001_init.sql`.
3. Добавить `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` и secret `SUPABASE_SECRET_KEY` в GitHub.
4. Выполнить bootstrap двух UUID.
5. Создать Render service и задать backend env.
6. Проверить `/health`.
7. Сохранить Render `/api/v1` URL как `VITE_API_URL`.
8. При необходимости настроить Supabase Auth Site URL / Redirect URLs для GitHub Pages.
9. Запустить `Deploy internal platform to Pages`.
10. Проверить вход обоими аккаунтами, RLS, файлы, задачу и программу.

## Security note

Publishable key безопасно размещать в браузере только при корректном RLS. Secret key обходит RLS и должен оставаться только в доверенной server-side среде. После перехода можно отключить legacy `anon`/`service_role` keys в Supabase Dashboard, когда Last used показывает, что они больше нигде не используются.
