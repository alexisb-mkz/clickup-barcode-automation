# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Function App (`function/barcode/`)

```bash
# Activate virtual environment (Windows)
.venv/Scripts/activate

# Run locally (Azurite must be running first — table service on port 10002)
func start

# Install dependencies
pip install -r requirements.txt
```

Azurite must be running with blob (10000) and table (10002) services before `func start`. The VS Code Azurite extension or `azurite --location ./azurite` from within `function/barcode/` handles this.

Deploy via VS Code Azure Functions extension: right-click the function app → **Deploy to Function App**. The `.vscode/settings.json` limits the deploy path to `function/barcode/` only.

### Frontend (`frontend/task-ui/`)

```bash
npm run dev       # local dev server on :5173 (requires VITE_FUNCTION_APP_URL in .env)
npm run build     # tsc type-check + vite build → dist/
npm run preview   # serve built dist/ locally
```

`VITE_FUNCTION_APP_URL` must be set at build time — Vite bakes it into the bundle. For local dev, add it to `frontend/task-ui/.env` (gitignored). Point it at `http://localhost:7071` for local function app.

SWA deploys automatically on push to `main` via GitHub Actions (`.github/workflows/`), which injects the production URL into the build.

---

## Architecture

### System Flow

```
ClickUp webhook (taskTagUpdated + "createpdf" tag)
  → http_trigger_task_parse
  → ClickUp API (fetch task + attachments)
  → MaintenancePDFGenerator (ReportLab)
  → Blob Storage (content/{task_id}.pdf)
  → write_task_snapshot() → TableCache (MERGE upsert)
  → event_grid_blob_trigger_send_email (EventGrid on new blob)
  → ACS Email with PDF attached

QR code on PDF contains:
  https://fa-clickup-barcode-automation.azurewebsites.net/api/http_trigger_barcodescan
    ?code={BarcodeScanFuncKey}&task_id={id}
  → 302 redirect → SWA /task/{id}

SWA /task/{id}
  → GET /api/task/{id}     (ClickUp live data + TableCache tech fields merged)
  → PUT /api/task/{id}     (updates ClickUp status/start_date + TableCache tech fields)
  → POST /api/task/{id}/attachment  (base64 → ClickUp attachment API)
  → GET /api/task/{id}/pdf          (stream from Blob Storage)
  → POST /api/translate             (Azure Translator proxy)
```

### Data Merge Strategy

The `GET /api/task/{id}` response merges two sources:
- **ClickUp** (always fetched first): `task_name`, `property_address`, `issue_description`, `action_items`, `start_date_ms`, `start_buffer_hours`, `task_status`, `translate_flag`, `attachments`
- **Table Storage** (tech-writable, MERGE upsert never overwrites these): `arrival_date_iso`, `completion_status`, `tech_notes`, `last_ui_update_at`

If ClickUp is unreachable, the function falls back to the cached Table Storage snapshot (`cache_stale: true` in response).

### Table Storage MERGE Pattern

All writes use `UpdateMode.MERGE` (`upsert_entity`). This means:
- `write_task_snapshot()` refreshes ClickUp-sourced fields without touching tech fields
- `update_tech_fields()` only touches the three tech-writable fields + `last_ui_update_at`
- Creating a PDF for an already-active task preserves the technician's saved data

### Auth Model

- `http_trigger_task_parse` and `http_trigger_barcodescan`: `AuthLevel.FUNCTION` (key in URL)
- All `/api/task/*` and `/api/translate` routes: `AuthLevel.ANONYMOUS`, CORS-restricted to the SWA origin
- CORS is controlled **only** via `host.json`. If any origins are configured in Azure Portal → Function App → API → CORS, `host.json` CORS is silenced entirely — keep Portal CORS empty.

### PDF Generation (`shared/pdf/`)

`MaintenancePDFGenerator` orchestrates three modules:
- `styles.py` — `PDFStyles` (ReportLab `ParagraphStyle` instances) + `PDFLayout` (dimension constants)
- `templates.py` — `MaintenanceRequestTemplate` (builds header, issue section, action items, image grid)
- `components.py` — `ClickableQRCode` (qrcode + ReportLab Flowable) and `ScaledImageGrid`

`translate_fn` is threaded through all build methods as an optional callable — pass `translate_text` when `translate_flag` is true, else `None` (identity lambda fallback).

### Frontend Language System

`LanguageContext` (`src/contexts/LanguageContext.tsx`) provides `lang` (`'en' | 'zh'`):
- `toggleLang()` — explicit user action, persists to `localStorage`
- `setLangAuto()` — auto-detection from `task.translate_flag`, does **not** write to `localStorage`
- `hasStoredLangPreference()` — guards against overwriting an explicit user choice

Translation is lazy-fetched via `useTaskTranslation` hook calling `POST /api/translate`, with in-memory cache keyed on `task_id + snapshot_written_at`. All UI strings use the `t(key, lang)` helper from `src/utils/i18n.ts`.

### ClickUp Status Mapping

`src/utils/statusMap.ts` maps UI `completion_status` values (`pending`/`in_progress`/`completed`) to ClickUp workspace status strings. The `clickupValue` strings must match the exact status names in the ClickUp workspace — verify them by inspecting `task_status` in the GET response.

### Quill Delta Parsing

ClickUp stores rich text as Quill Delta JSON (`value_richtext` field). `parse_quill_delta()` in `shared/utils/helpers.py` converts this to `[{text, type}]` segments where `type` is `"bullet"`, `"ordered"`, or `None`. The same parsing logic runs in both the PDF generator (Python) and the React frontend (the API returns pre-parsed `action_items` array).
