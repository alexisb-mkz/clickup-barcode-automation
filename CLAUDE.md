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
  → write_task_snapshot() → TableCache (MERGE upsert, update_snapshot_time=True)
  → event_grid_blob_trigger_send_email (EventGrid on new blob)
  → ACS Email with PDF attached

QR code on PDF contains:
  https://fa-clickup-barcode-automation.azurewebsites.net/api/http_trigger_barcodescan
    ?code={BarcodeScanFuncKey}&task_id={id}
  → 302 redirect → SWA /task/{id}

SWA /task/{id}
  → GET /api/task/{id}                    (ClickUp live data + TableCache tech fields merged)
  → PUT /api/task/{id}                    (updates ClickUp status/start_date/contractor_notes + TableCache tech fields)
  → POST /api/task/{id}/attachment        (base64 → ClickUp attachment API)
  → GET /api/task/{id}/pdf               (stream from Blob Storage)
  → POST /api/task/{id}/regenerate-pdf   (regenerate PDF from current ClickUp data)
  → POST /api/translate                  (Azure Translator proxy)
```

### Data Merge Strategy

The `GET /api/task/{id}` response merges two sources:
- **ClickUp** (always fetched first): `task_name`, `property_address`, `issue_description`, `action_items`, `start_date_ms`, `start_buffer_hours`, `task_status`, `translate_flag`, `attachments`, `date_updated`
- **Table Storage** (tech-writable, MERGE upsert never overwrites ClickUp fields): `arrival_date_iso`, `completion_status`, `tech_notes`, `last_ui_update_at`

The response also includes `snapshot_written_at` (when PDF was last generated) and `pdf_stale_fields` (list of field keys that differ from their values at PDF generation time).

`tech_notes` initialisation order: Table Storage value → fallback to ClickUp "Contractor Notes" custom field value if Table Storage has none. This means the first time a technician visits a task, any notes already in ClickUp are pre-populated.

`contractor_notes` and `contractor_notes_field_id` are extracted from ClickUp on every GET but are **never** sent to the frontend — they are internal fields stripped from the response before it is returned.

If ClickUp is unreachable, the function falls back to the cached Table Storage snapshot (`cache_stale: true` in response).

### Table Storage MERGE Pattern

All writes use `UpdateMode.MERGE` (`upsert_entity`). This means:
- `write_task_snapshot(task_id, data, pdf_blob_url, update_snapshot_time=True)` — when `True` (PDF generation), refreshes all ClickUp-sourced fields AND writes `snapshot_written_at` + `pdf_*` baseline fields frozen at generation time. When `False` (GET refresh), only updates live ClickUp fields without touching `snapshot_written_at` or `pdf_*` fields.
- `update_tech_fields()` only touches the three tech-writable fields + `last_ui_update_at`
- `seed_pdf_snapshot_fields()` — one-time MERGE write of `pdf_*` fields for tasks that existed before the field-diff feature was deployed; called on first GET when `pdf_task_name` is absent from the entity
- Creating a PDF for an already-active task preserves the technician's saved data

### PDF Staleness Detection

`pdf_*` fields (`pdf_task_name`, `pdf_property_address`, `pdf_issue_description`, `pdf_action_items_raw`, `pdf_start_date_ms`) store the ClickUp field values frozen at PDF generation time. On every GET, `_handle_task_get` diffs the current ClickUp values against these `pdf_*` fields to produce `pdf_stale_fields`.

Staleness side effects (only when `snapshot_written_at` is set and `pdf_*` baseline exists):
1. **`pdf-stale` tag** — added to the ClickUp task via `_sync_pdf_stale_tag()`; removed after regeneration
2. **"Warnings" custom field** — set to a Quill Delta red-strong banner via `_sync_pdf_warnings_field()` listing changed fields and timestamps (ET); cleared after regeneration

When a baseline doesn't exist (`pdf_task_name is None`), `seed_pdf_snapshot_fields()` is called to initialise it from current values, and tag/warning sync is skipped for that GET.

Regeneration can be triggered two ways:
- **Technician portal** — `POST /api/task/{task_id}/regenerate-pdf` endpoint
- **ClickUp** — re-adding the `createpdf` tag triggers `http_trigger_task_parse`, which regenerates and calls `write_task_snapshot(update_snapshot_time=True)`, clearing the stale state

The frontend `PdfLink` component shows a yellow warning with the changed field names when `pdf_stale_fields.length > 0`. Background polling (`useTask.ts`, 30s interval, paused when tab hidden) refreshes task data so the warning appears without a manual page reload.

### PUT Response

`PUT /api/task/{id}` returns the saved tech fields plus `last_ui_update_at`. When `arrival_date_iso` is in the payload, the response also includes `start_date_ms` (the millisecond equivalent) so the frontend can update `ScheduledWindow` optimistically without waiting for the next GET.

Clearing the arrival date: send `arrival_date_iso: ""` (empty string, key must be present). The backend detects the key's presence with `"arrival_date_iso" in body` (not truthiness), sends `start_date: null` to ClickUp, and returns `start_date_ms: ""`.

### ClickUp Custom Field Sync

When `tech_notes` is saved via PUT, the backend also syncs the value to the ClickUp "Contractor Notes" custom field (case-insensitive name match):

1. Read `contractor_notes_field_id` from the Table Storage snapshot (written by `write_task_snapshot` on the preceding GET)
2. If not cached (e.g. first save before a GET has run), fall back to a live ClickUp GET to find the field ID
3. `POST /api/v2/task/{task_id}/field/{field_id}` with `{"value": notes_text}`
4. Failure is non-fatal — logs a warning, always returns 200 so the Table Storage save is never blocked

Similarly, `arrival_date_iso` always syncs to ClickUp's top-level `start_date` field on every PUT.

### Auth Model

- `http_trigger_task_parse` and `http_trigger_barcodescan`: `AuthLevel.FUNCTION` (key in URL)
- All `/api/task/*` and `/api/translate` routes: `AuthLevel.ANONYMOUS`, CORS-restricted to the SWA origin
- CORS is controlled **only** via `host.json`. If any origins are configured in Azure Portal → Function App → API → CORS, `host.json` CORS is silenced entirely — keep Portal CORS empty.

### PDF Generation (`shared/pdf/`)

`MaintenancePDFGenerator` orchestrates three modules:
- `styles.py` — `PDFStyles` (ReportLab `ParagraphStyle` instances) + `PDFLayout` (dimension constants)
- `templates.py` — `MaintenanceRequestTemplate` (builds header, issue section, action items, image grid)
- `components.py` — `ClickableQRCode` (qrcode + ReportLab Flowable), `ScaledImageGrid`, and `CJKFontManager`

**CJK font handling:** `CJKFontManager` (in `components.py`) registers a CJK-capable font under the family name `CJKFont` at module load time. All `ParagraphStyle` instances in `PDFStyles` use `fontName=_cjk.font_name`. Styles that require bold text (section headers) use `<b>...</b>` markup tags rather than a bold parent style — this lets ReportLab resolve bold through the registered font family, which supports both Latin and CJK characters. Section header and subtitle styles use `parent=Normal` (not `Heading2`) to avoid inheriting `Helvetica-Bold` from the default stylesheet, which would break CJK bold resolution.

**Translation:** `translate_fn` is threaded through all build methods as an optional callable — pass `translate_text` when `translate_flag` is true, else `None` (identity lambda fallback). **`property_address` must never be passed through `translate_fn`** — it is applied to `normalize_address()` directly. When `translate_fn` is set, dates use 24-hour format (`%H:%M`); otherwise 12-hour (`%I:%M %p`). Section header strings ("Issue Description", "Action Items") are passed through `t()` then wrapped in `<b>` tags.

### Frontend Language System

`LanguageContext` (`src/contexts/LanguageContext.tsx`) provides `lang` (`'en' | 'zh'`):
- `toggleLang()` — explicit user action, persists to `localStorage`
- `setLangAuto()` — auto-detection from `task.translate_flag`, does **not** write to `localStorage`
- `hasStoredLangPreference()` — guards against overwriting an explicit user choice

Translation is lazy-fetched via `useTaskTranslation` hook calling `POST /api/translate`. The hook translates `task_name`, `issue_description`, `tech_notes`, and all `action_items` text in a single batched request. `property_address` is intentionally excluded. Results are cached in-memory keyed on `task_id + snapshot_written_at`.

All UI strings use the `t(key, lang)` helper from `src/utils/i18n.ts`.

Date formatting uses `formatDisplayDate(iso, lang)` in `src/utils/dateUtils.ts`, which passes `'en-US'` or `'zh-CN'` to `toLocaleString` with `hour12: lang !== 'zh'` — `Intl.DateTimeFormat` handles locale-appropriate month names and weekday names automatically.

### Scheduled Window / Date Picker

`ScheduledWindow` (`src/components/ScheduledWindow.tsx`) is both the display and the editable date picker. The start date is rendered as a styled button; clicking opens an inline date/time input. In English (`lang === 'en'`), a native `datetime-local` input is used. In Chinese (`lang === 'zh'`), a custom `ChineseDateTimePicker` component renders — it provides a calendar grid with Chinese month names, guaranteed 24-hour `<select>` dropdowns for hour/minute, and 确认/清除 (confirm/clear) buttons. Clear sends `arrival_date_iso: ""` to the backend.

Source of truth is always `task.start_date_ms` (from ClickUp). After saving, the PUT response returns `start_date_ms` so the component updates optimistically without a page reload.

`TechNotes` (`src/components/TechNotes.tsx`) syncs its draft to the `value` prop whenever the prop changes externally (e.g. translation arrives or language toggles), guarded by a `focusedRef` so an in-progress edit is never clobbered.

### ClickUp Status Mapping

`src/utils/statusMap.ts` maps UI `completion_status` values (`pending`/`in_progress`/`completed`) to ClickUp workspace status strings. The `clickupValue` strings must match the exact status names in the ClickUp workspace — verify them by inspecting `task_status` in the GET response.

### Quill Delta Parsing

ClickUp stores rich text as Quill Delta JSON (`value_richtext` field). `parse_quill_delta()` in `shared/utils/helpers.py` converts this to `[{text, type}]` segments where `type` is `"bullet"`, `"ordered"`, or `None`. The same parsing logic runs in both the PDF generator (Python) and the React frontend (the API returns pre-parsed `action_items` array).

The ClickUp "Warnings" custom field is written as a Quill Delta with `advanced-banner-color: "red-strong"` attributes. Each line is a text insert followed by a newline insert carrying the banner attributes. Bullet lines additionally carry `"list": {"list": "bullet"}`. Block IDs are generated with `f"block-{uuid.uuid4()}"`.
