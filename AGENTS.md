# AGENTS.md — Druk internal platform

This file is the primary working guide for coding agents in this repository, especially GPT-5.6 Sol. Read it before changing code.

## 0. Operating mode

- Bias toward completing requested work end-to-end, but do not broaden scope without a concrete reason.
- Inspect the current implementation before editing. This project has changed architecture several times; old comments and parts of `README.md` can be stale.
- Preserve working behavior. Prefer small, reversible changes over rewrites.
- Never expose secrets, auth UUIDs, service keys, GitHub tokens, or private workspace data in commits, logs, screenshots, or user-facing output.
- Do not change `main` unless the user explicitly asks. The internal application lives on `internal-platform`; `main` is the public landing page.
- Do not deploy production unless the user asks for a deploy. A push to `internal-platform` can trigger CI and Vercel, so understand deployment consequences before committing.
- If the user says to stop or defer a current bugfix, stop it. Do not opportunistically finish unrelated work.

## 1. Product in one paragraph

Druk Internal is a private operating system for the Druk startup team. It combines dashboard/focus, Jira-like tasks, accelerator/program applications, reusable application answers, files/materials, meetings/events, decisions, comments, bug reports, analytics, team settings, and read-only GitHub issue sync. UI copy is primarily Russian.

The product is optimized for a very small team, currently two technical founders. Favor clarity and speed over enterprise abstraction.

## 2. Canonical branches and hosting

### Branches

- `main` — public marketing landing. Treat as separate product surface.
- `internal-platform` — canonical source branch for the internal platform.
- Other branches may be temporary experiments or previews. Do not merge or deploy them unless explicitly requested.

### Current production architecture

The current architecture is **Vercel + Supabase-first**, while the FastAPI backend is intentionally retained for future self-hosting.

```text
Browser
  ├─ React + TypeScript + Vite on Vercel
  ├─ Supabase Auth
  ├─ direct Supabase PostgREST / Storage requests under user JWT + RLS
  └─ Vercel serverless API only for privileged GitHub operations

Future / fallback:
Browser -> FastAPI -> Supabase / GitHub
```

Important: `README.md` still contains older GitHub Pages / Render-centric architecture notes. For current behavior, trust these files first:

1. `frontend/src/lib/api.ts`
2. `frontend/src/lib/supabase.ts`
3. `frontend/api/v1/github/[...path].ts`
4. `frontend/vercel.json`
5. `supabase/migrations/*`
6. `backend/app/*` for preserved FastAPI parity

## 3. Repository map

```text
.
├─ frontend/
│  ├─ src/
│  │  ├─ App.tsx                 # most UI/pages; large monolithic file
│  │  ├─ Markdown.tsx            # lightweight Markdown renderer
│  │  ├─ styles.css              # main visual system
│  │  ├─ stability.css           # late CSS fixes / layout hardening
│  │  ├─ generated-art.css       # artwork placement/cropping rules
│  │  ├─ generatedArtwork.ts     # resolves current artwork URLs
│  │  └─ lib/
│  │     ├─ api.ts               # compatibility API facade; mostly direct Supabase
│  │     ├─ supabase.ts          # browser Supabase client + env validation
│  │     ├─ prefetch.ts          # background warm-up of common pages
│  │     └─ date.ts
│  ├─ api/v1/github/[...path].ts # Vercel function for privileged GitHub sync
│  ├─ public/                    # static images/favicon and generated artwork
│  ├─ package.json
│  ├─ vite.config.ts
│  └─ vercel.json
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ core.py                 # original/primary FastAPI routes
│  │  ├─ extended.py             # newer product routes
│  │  ├─ auth.py                 # Supabase session validation + short cache
│  │  ├─ db.py                   # Supabase HTTP client + pooled connections
│  │  ├─ files.py
│  │  └─ bug_reports.py
│  └─ tests/
├─ supabase/
│  └─ migrations/
├─ scripts/
└─ .github/workflows/
```

`frontend/src/App.tsx` is intentionally large today. Do not refactor it simply because it is large. Extract a component only when that materially reduces risk or repeated complexity for the requested task.

## 4. Frontend stack and conventions

- React 19
- TypeScript
- Vite 7
- React Router with `HashRouter`
- TanStack Query
- Supabase JS client
- Zod for environment/response validation
- Node 24 (`frontend/package.json` engines and CI)

### Commands

Run from `frontend/`:

```bash
npm ci
npm run lint
npm run typecheck
npm test
npm run build
npm run dev
```

Before declaring frontend work complete, run at minimum:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

Do not claim a build is green without actual successful output.

### UI conventions

- Product language: Russian.
- Visual style: warm cream/green nature aesthetic, rounded cards, restrained shadows, Druk stone mascot imagery.
- Keep the layout fluid on large displays; avoid reintroducing a hard narrow global `max-width` that wastes desktop space.
- Main responsive breakpoints already exist around desktop/tablet/mobile widths. Inspect existing CSS before adding new breakpoint systems.
- Prefer `min-width: 0`, `minmax(0, ...)`, and overflow containment when fixing grid/flex layout issues.
- Keep interactive controls visibly discoverable. Do not hide core actions behind unexplained icons.
- Avoid destructive delete when an archive state is appropriate.

### CSS layering

There are multiple historical CSS layers. Later files/rules can intentionally override earlier ones. Before changing a broken visual:

1. find the element/class in `App.tsx`;
2. search all CSS files for the selector;
3. identify which rule wins;
4. patch the smallest relevant layer.

Do not stack another `!important` override unless you have confirmed why the earlier rule cannot be corrected safely.

## 5. Data access architecture — critical

`frontend/src/lib/api.ts` presents an API-like interface to the UI, but most routes are handled **directly against Supabase** in `directApi()`.

Pattern:

```text
App.tsx -> api('/tasks')
              |
              +-> directApi(): Supabase JS + RLS
              |
              +-> fallback serverApi(): Vercel/FastAPI endpoint when route is privileged or unsupported
```

Do not assume every `api('/...')` call reaches FastAPI.

When adding a normal CRUD feature, first decide whether it can safely run direct-to-Supabase under RLS. Prefer direct Supabase for ordinary workspace data. Use server-side code when a secret or privileged external API is required.

### Browser auth/workspace context

`api.ts` caches a single workspace context for the logged-in user. The product currently assumes a user belongs to exactly one workspace. Preserve that invariant unless the user explicitly requests multi-workspace support.

### Query cache

TanStack Query cache is persisted client-side and common pages are prefetched. When changing query shapes or semantics, consider stale persisted data. If a change is incompatible with old cache data, bump the cache key/version deliberately rather than adding random reload workarounds.

## 6. Supabase, RLS, and migrations

Supabase is the source of truth for Auth, Postgres, private Storage, and RLS.

Current migration sequence includes:

- `001_init.sql` — initial schema/RLS/storage
- `003_design_expansion.sql` — expanded product model
- `004_collaboration_comments.sql` — generic comments
- `005_bug_reports.sql` — bug reports
- `006_direct_client_hardening.sql` — storage/direct-client hardening
- `007_answer_library_program_sync.sql` — program answer -> library synchronization
- `008_task_archiving.sql` — task archive support

Never edit an already-applied migration to change production state. Add a new numbered migration.

For schema changes:

1. inspect the latest migration and existing constraints/policies;
2. add an idempotent or safely forward-only migration;
3. preserve RLS;
4. update frontend direct-Supabase behavior;
5. update FastAPI parity where the same feature is expected to work after self-hosting;
6. add/update tests where practical.

### Security rules

- Browser may contain only the Supabase publishable key (`sb_publishable_...`).
- Never put `sb_secret_...`, service-role credentials, or GitHub secrets in `VITE_*` variables.
- User data access must be bounded by RLS and workspace membership.
- Private files belong in the `workspace-files` bucket.
- Deletion rules must protect files that are already referenced by immutable/submission snapshots.

## 7. Important product invariants

### Answers

`answer_library` is intended to be the reusable global answer corpus for the workspace.

Program-specific answers live in `program_answers`, but answers created inside programs must also be represented/synchronized in `answer_library` according to migration `007_answer_library_program_sync.sql`.

Do not implement program answers as an isolated silo again.

When editing this area, distinguish:

- universal/reusable answer in `answer_library`;
- program-specific adapted answer in `program_answers`;
- `source_answer_id`, which records origin when applicable.

Do not silently overwrite a reusable source answer with a program-specific adaptation unless the data model explicitly calls for it.

### Markdown answers

There is a lightweight renderer in `frontend/src/Markdown.tsx` supporting common Markdown structures, including headings, emphasis, code, links, lists, blockquotes, fenced code blocks, and pipe tables.

At the time this guide was written, Markdown editing/rendering work was still evolving. Inspect the current UI before assuming every answer input already behaves like Obsidian. If implementing rich answer editing, preserve raw Markdown as the stored value and render it safely; do not convert stored answers into HTML.

### Tasks

Tasks use statuses:

- `planned`
- `in_progress`
- `done`

They also have an `archived` state. Completed tasks should be viewable by default where the product expects them; archival is distinct from deletion.

The task board is intended to feel Jira-like:

- drag between statuses;
- explicit edit/detail action;
- clear done/archive behavior;
- long task sets must remain usable with scrolling rather than endlessly stretching the page.

Do not make GitHub Issues availability a hard dependency for rendering local tasks. GitHub is supplemental.

### Programs

Programs contain status, deadlines, checklist items, answers, files, submissions, and optional events. Submission snapshots are intentionally historical. Do not mutate old snapshots as live records change.

Checklist UI must support both checking items and adding items without controls collapsing to checkbox dimensions.

### Comments

`entity_comments` is polymorphic across answers, program answers, and files. Backend/direct-client code validates workspace access. Keep comments separate from submitted application snapshots unless the product requirement changes.

### Files

Files are private workspace assets. Program file links are relational references. Signed URLs should be short-lived. Do not expose raw private Storage URLs.

### Bug reports

Bug reports can contain description, page URL, browser user agent, and optional screenshot. Screenshot handling must keep file type/size validation and private Storage behavior.

## 8. GitHub integration

GitHub issue data is supplemental and should never block core app pages.

Current direction:

- cached/read data can live in Supabase and be read directly;
- privileged sync that needs `GITHUB_TOKEN` runs server-side via `frontend/api/v1/github/[...path].ts` on Vercel;
- FastAPI keeps equivalent integration for future self-hosting.

Never expose `GITHUB_TOKEN` to browser code.

When a GitHub API request fails, degrade the GitHub block, not the whole Tasks or Settings page.

## 9. FastAPI preservation rules

FastAPI is not the primary hot path in the current Vercel/Supabase deployment, but it is intentionally retained because the team expects to move to self-hosting.

Therefore:

- do not delete backend routes merely because the frontend now talks directly to Supabase;
- when adding important business behavior, consider whether FastAPI needs parity;
- preserve pooled HTTP behavior in `backend/app/db.py`;
- preserve short-lived authenticated workspace caching in `backend/app/auth.py` unless replacing it with a demonstrably better self-hosted approach;
- keep backend tests passing.

Backend validation:

```bash
cd backend
pip install -r requirements.txt
python -m compileall -q app
pytest -q -m 'not integration'
```

CI uses placeholder Supabase env values for non-integration tests.

## 10. Artwork and static assets

Generated Druk artwork has historically broken because paths changed between GitHub Pages and Vercel and because images were embedded as base64 in JS.

Current stable rule: artwork should be served as **normal static assets**, not giant base64 data URLs inside JavaScript.

Relevant files:

- `frontend/src/generatedArtwork.ts`
- `frontend/src/generated-art.css`
- `frontend/public/`

Use `import.meta.env.BASE_URL` when constructing static paths that must work under both `/` and a subpath.

Do not casually rename or move artwork files without updating both URL construction and CSS placement.

Image placement expectations:

- home: wide hero, text breathing room, mascot generally on the right;
- sidebar/rail: tall scenic image, usually landscape-only/no mascot when requested;
- page side banner: medium horizontal/compact composition;
- lower-page/nature note: wide panoramic composition.

For quality improvements, prefer high-quality JPEG/PNG or appropriately encoded WebP/AVIF as separate static files. Keep enough resolution for high-DPI desktop displays without embedding multi-megabyte payloads in the JS bundle.

## 11. Deployment behavior

### Vercel

`frontend/vercel.json` is the deployment config. Production tracks `internal-platform`. The Vercel project root is `frontend`.

Expected production environment variables:

```text
VITE_SUPABASE_URL
VITE_SUPABASE_PUBLISHABLE_KEY
GITHUB_TOKEN             # server-side only
```

`VITE_API_URL` is optional in the Supabase-first deployment and can later point to self-hosted FastAPI.

### GitHub Pages

Legacy GitHub Pages workflows still exist because the public landing and previous internal deployment used them. Do not assume Pages is the active internal production host.

### Render

Render configuration/backend history remains in the repository, but current internal production should not depend on Render for normal CRUD.

## 12. CI and definition of done

Workflow: `.github/workflows/platform-ci.yml`.

For normal code changes, definition of done is:

- requested behavior implemented;
- no unrelated feature regression;
- frontend lint passes;
- frontend typecheck passes;
- frontend tests pass;
- frontend production build passes;
- backend compile/tests pass if backend touched or shared behavior changed;
- DB migration applied only when the user asked for/authorized production DB changes;
- deploy verified only when deployment was requested.

Do not report "deployed" merely because code was pushed. Verify the actual hosting provider/status.

## 13. Working with the monolithic App.tsx

Because `App.tsx` is large, careless global replacements are risky.

Recommended process:

1. search for the exact page/component/function;
2. inspect surrounding state, queries, mutations, and CSS class names;
3. make narrow edits;
4. search for other occurrences before renaming classes or query keys;
5. run TypeScript and build immediately after structural JSX edits.

Avoid one-off generated patch scripts unless direct editing is genuinely impractical. If a temporary patch script/workflow is created, remove it after use.

## 14. Common failure modes to avoid

- Reintroducing Render latency into ordinary CRUD after the Supabase-first migration.
- Making local Tasks/Settings wait on GitHub serverless calls.
- Breaking Vercel asset paths by assuming `/Druk/` or GitHub Pages base paths in production.
- Embedding large artwork as base64 inside JS.
- Treating `answer_library` and program answers as unrelated stores.
- Deleting completed tasks instead of archiving them.
- Mutating historical program submission snapshots.
- Adding a schema column without RLS/policy review and direct-client support.
- Updating only direct Supabase code but leaving future FastAPI self-hosting broken for an important feature.
- Hiding loading/error problems behind huge retry delays instead of fixing dependency boundaries.
- Claiming a fix is live without checking CI/deployment state.

## 15. How to approach a new request

Use this sequence unless the task clearly requires something else:

1. Determine whether the request is frontend-only, database, privileged server action, or cross-stack.
2. Inspect the canonical implementation, not just `README.md`.
3. Identify invariants affected (RLS, answer sync, snapshots, archive, private files, cache).
4. Implement the smallest coherent change.
5. Validate locally/CI-equivalent.
6. If DB changes are needed, add a new migration and apply it only when authorized.
7. If deployment is requested, push to the correct branch and verify Vercel/other target actually succeeded.
8. Report exactly what changed, what was tested, and what remains intentionally untouched.

## 16. Current repository-specific caution

A separate HQ artwork experiment/preview branch may exist. It is not production source unless explicitly merged. Do not infer that preview/temporary branches are approved simply because they exist.

Likewise, unfinished Markdown/editor or artwork experiments from prior sessions should not be continued unless they are part of the current user request.

---

If this file conflicts with current executable code, inspect recent commits and the relevant implementation first. Update `AGENTS.md` when architecture or project invariants materially change so the next coding agent does not repeat obsolete assumptions.
