# Development TODOs

## [ ] 1. Translate timestamps in date pickers

**Where:** `frontend/task-ui/src/components/ArrivalDatePicker.tsx`, `ScheduledWindow.tsx`, `src/utils/dateUtils.ts`

Date/time strings displayed in the UI (scheduled window range, arrival date display) are formatted in English (e.g. "February 25, 2026 at 10:00 AM"). When the user switches to Chinese, these should render in a Chinese-friendly format.

- Format dates using `Intl.DateTimeFormat` with `locale` based on current `lang` (`'en-US'` / `'zh-CN'`)
- Pull `lang` from `useLanguage()` in the relevant components
- `dateUtils.ts` formatting helpers may need a `lang` parameter added

---

## [ ] 2. Warn when PDF may be outdated + allow technician to regenerate

**Where:** `function/barcode/function_app.py`, `frontend/task-ui/src/components/PdfLink.tsx`, `frontend/task-ui/src/api/taskApi.ts`

If a task's ClickUp fields have been updated after the PDF was last generated, the technician sees stale content. They should be able to regenerate and resend without involving a manager.

### Backend — new endpoint

Add `POST /api/task/{task_id}/regenerate-pdf` (`auth_level=ANONYMOUS`):
1. Fetch task from ClickUp API (same as `_handle_task_get`)
2. Re-run PDF generation (reuse `MaintenancePDFGenerator` + same logic as `http_trigger_task_parse`)
3. Upload to blob (`overwrite=True`) — the existing EventGrid blob trigger fires automatically, resending the email
4. Call `write_task_snapshot()` to refresh `snapshot_written_at`
5. Return `{"ok": true, "snapshot_written_at": "..."}` on success

Expose `date_updated` from ClickUp in `_extract_task_fields` and the GET response so the frontend can compare it to `snapshot_written_at`.

### Frontend — stale warning + regenerate button

In `PdfLink.tsx` (or inline in `TaskPage`):
- Accept `dateUpdatedMs: string` and `snapshotWrittenAt: string | null` as props
- If `dateUpdatedMs > snapshotWrittenAt` (parse both to timestamps), show a yellow warning badge on the PDF button (e.g. "⚠ Task was updated — PDF may be outdated")
- Show a **"Regenerate PDF"** button that calls `POST /api/task/{task_id}/regenerate-pdf`
- While regenerating: disable button, show spinner/"Regenerating..."
- On success: hide warning, update `snapshot_written_at` in local task state, show "✓ PDF regenerated and email resent"
- On failure: show error message

### New items needed
- `regeneratePdf(taskId)` in `taskApi.ts`
- `useRegeneratePdf` hook (or inline state in `PdfLink`) for loading/success/error
- `date_updated` added to `Task` type in `types/task.ts`
- i18n strings for new UI states in `i18n.ts`

---

## [ ] 3. Sync tech notes with ClickUp

**Where:** `function/barcode/function_app.py` (`_handle_task_put`), `function/barcode/shared/utils/table_cache.py`

Currently `tech_notes` is stored only in Table Storage. It should also be written back to ClickUp so notes are visible in the ClickUp task.

Decide on target field in ClickUp:
- **Option A:** Append/overwrite a custom field (e.g. "Tech Notes") via `PUT /api/v2/task/{id}` with `custom_fields`
- **Option B:** Post as a task comment via `POST /api/v2/task/{id}/comment`

In `_handle_task_put`: after writing tech fields to Table Storage, if `tech_notes` is present, make the additional ClickUp API call. Handle failure non-fatally (log warning, still return 200 so the local save isn't lost).

---

## [ ] 4. Assignee field + Google Calendar event

**Where:** New work across backend + frontend

When a task is assigned to someone in ClickUp, automatically create (or update) a Google Calendar event on that person's calendar for the scheduled arrival window.

### Backend
- `_extract_task_fields`: extract `assignees` from ClickUp task (`data.get("assignees", [])`) — each has `id`, `username`, `email`
- Expose `assignees` in the GET response
- New function or extend `_handle_task_put`: when `arrival_date_iso` is saved, trigger a Google Calendar API call
  - Requires Google service account + Calendar API credentials (store in Key Vault)
  - Map ClickUp assignee email → Google Calendar ID
  - Create/update event with `summary`, `start`, `end` (start + `start_buffer_hours`), `attendees`
  - Store returned `google_event_id` in Table Storage so subsequent saves can update rather than duplicate

### Frontend
- Display assignee name(s) in `TaskHeader` (read-only)
- No UI input needed for calendar — it fires automatically when arrival date is saved

### New env vars needed
- `GoogleServiceAccountJson` — Key Vault secret (service account credentials JSON)
- `GoogleCalendarId` — default calendar, or map per-assignee

### Dependencies to add (`requirements.txt`)
- `google-api-python-client`
- `google-auth`
