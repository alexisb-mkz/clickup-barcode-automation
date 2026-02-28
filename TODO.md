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

---

## [ ] 5. Email admin when arrival date or task status changes

**Where:** `function/barcode/function_app.py` (`_handle_task_put`), `function/barcode/shared/utils/email.py` (new helper)

When a technician saves an `arrival_date_iso` or `completion_status` change via the UI, send a notification email to the admin so they can track field progress without checking ClickUp manually.

### Trigger conditions

Only send when the value actually changes:
- `arrival_date_iso` is present in the PUT body **and** differs from the cached value in Table Storage
- `completion_status` is present in the PUT body **and** differs from the cached value in Table Storage

Read the previous values from `read_task_snapshot(task_id)` before writing to compare.

### Email content

- **Subject:** `[Task Update] {task_name} — {change summary}` (e.g. "Arrival set to Feb 25, 10:00 AM" or "Status → Completed")
- **Body:** task name, property address, what changed (old → new), technician's `last_ui_update_at`, link to ClickUp task (`https://app.clickup.com/t/{task_id}`)
- Send via ACS Email (`EmailClient`), same sender/connection string as the PDF email
- Recipient: new env var `AdminEmail` (add to `local.settings.json` and Azure app settings)

### Implementation notes

- Extract the send logic into `shared/utils/email.py` (`send_admin_notification(task_id, task_name, property_address, changes: list[dict])`) to keep `function_app.py` clean and reuse it for future notifications
- `changes` is a list of `{"field": str, "old": str, "new": str}` dicts
- Handle failure non-fatally: log warning, still return 200 so the tech save is never blocked
- Format `arrival_date_iso` values as human-readable strings (e.g. `"Feb 25, 2026 10:00 AM"`) in the email body, not raw ISO

### New env vars needed
- `AdminEmail` — recipient address for change notifications

---

## [ ] 6. Send automated SMS to tenant when arrival date is set

**Where:** `function/barcode/function_app.py` (`_handle_task_put`), new SMS helper

When a technician saves an `arrival_date_iso`, automatically text the tenant associated with the ClickUp task to notify them of the scheduled arrival time.

### Trigger condition

Send when `arrival_date_iso` is present in the PUT body and differs from the cached value in Table Storage (same change-detection pattern as TODO #5).

### SMS content

- "Hi [tenant name], a maintenance technician is scheduled to arrive at [property address] on [formatted date/time]. Reply STOP to opt out."
- Format the date in a human-readable, locale-appropriate way (reuse `formatDisplayDate` logic or equivalent in Python)

### Tenant phone number

- Add a "Tenant Phone" custom field to the ClickUp task (or read from an existing contact field)
- Extract it in `_extract_task_fields` and store in the Table Storage snapshot so it is available during `_handle_task_put` without an extra ClickUp GET

### SMS provider options to evaluate

1. **Azure Communication Services SMS** — native to the existing Azure stack; requires provisioning an ACS phone number
2. **Twilio** — widely used, simple API, pay-per-message

### Implementation notes

- Add SMS send logic to a new `shared/utils/sms.py` helper (`send_tenant_arrival_notification(to_number, tenant_name, property_address, arrival_iso)`)
- Handle failure non-fatally — log warning, still return 200 so the tech save is never blocked
- Opt-out / STOP handling depends on provider (ACS and Twilio both handle replies automatically for compliant numbers)

### New env vars needed
- `SmsConnectionString` or `TwilioAccountSid` / `TwilioAuthToken` — SMS provider credentials
- `SmsFromNumber` — the provisioned sender number

---

## [ ] 7. Sync Buildium tenant contacts into ClickUp as a multipick list

**Type:** Research + automation — investigate Buildium API, then build a sync job

Pull tenant contact information (name, phone, unit) from the Buildium property management API and populate a ClickUp custom field so that maintenance tasks can reference the correct tenant(s) and trigger automated notifications (see TODO #6).

### Buildium API investigation

- Authenticate via Buildium REST API (API key or OAuth — check Buildium account plan for API access)
- Endpoints to explore:
  - `GET /v1/leases` — active leases with unit and tenant info
  - `GET /v1/leases/{leaseId}/tenants` — tenant names and contact details per lease
  - `GET /v1/units` — units with property/address linkage
- Confirm whether phone numbers are returned and in what format

### ClickUp integration

- Create (or reuse) a **multipick dropdown** custom field named "Tenants" on the ClickUp task list
- Each option = one tenant entry formatted as `"[Name] — [Unit] — [Phone]"` or structured as separate fields
- Keep the option list in sync with active Buildium leases: add new tenants, mark or remove ended leases
- ClickUp API for managing custom field options: `POST /api/v2/list/{list_id}/field` (create field) and `PUT /api/v2/field/{field_id}` (update options)

### Sync job

- Run on a schedule (e.g. Azure Timer Trigger, daily or on-demand) to refresh the ClickUp tenant list from Buildium
- New Azure Function: `timer_trigger_sync_tenants` — fetches active leases from Buildium, diffs against current ClickUp field options, adds/removes as needed
- Store the Buildium → ClickUp option ID mapping in Table Storage so the SMS sender (TODO #6) can resolve a selected option back to a phone number without re-fetching Buildium

### Notification flow (end state)

1. Manager creates a ClickUp task and selects tenant(s) from the "Tenants" multipick field
2. `http_trigger_task_parse` (or a new webhook) reads the selected tenant(s) and their phone numbers from the mapping table
3. When a technician sets `arrival_date_iso`, the SMS helper (TODO #6) texts all selected tenants automatically

### New env vars needed
- `BuildiumApiKey` — Buildium REST API credential
- `BuildiumBaseUrl` — e.g. `https://api.buildium.com`

---

## [ ] 8. Sync Buildium property addresses into ClickUp "Property Address" custom field options

**Type:** Automation — build a sync job alongside TODO #7

Keep the ClickUp "Property Address" custom field option list automatically up to date with the properties managed in Buildium, so managers select from a canonical list rather than typing addresses freehand.

### Buildium API

- `GET /v1/properties` — returns all properties with full address (street, unit, city, state, zip)
- `GET /v1/units` — individual units within a property; use if per-unit granularity is needed (e.g. "123 Main St — Unit 4B")
- Reuse the Buildium auth established in TODO #7 (`BuildiumApiKey` / `BuildiumBaseUrl`)

### ClickUp sync

- Target field: the existing "Property Address" custom field on the task list (currently a plain text field — may need to be converted to a **dropdown** type for managed options)
- Investigate whether converting the field type from text → dropdown is feasible without losing existing task data; if not, create a separate "Property (select)" field and migrate
- Sync logic: fetch all active Buildium properties, diff against current ClickUp dropdown options, add new addresses and remove/archive properties that are no longer active
- ClickUp API: `PUT /api/v2/field/{field_id}` to update the options array

### Sync job

- Extend `timer_trigger_sync_tenants` (TODO #7) to also sync property addresses in the same run, or create a dedicated `timer_trigger_sync_properties` function
- Run daily or triggered manually via an HTTP endpoint for on-demand refresh
- Log added/removed options for auditability

### New env vars needed
- Shared with TODO #7 (`BuildiumApiKey`, `BuildiumBaseUrl`) — no additional vars required

---

## [ ] 9. Flag ClickUp task when fields are changed after PDF was generated

**Type:** Investigation + light implementation — assess feasibility before building

When a ClickUp task's fields are updated after the PDF was last generated (`snapshot_written_at`), automatically add a tag or update a custom field on the ClickUp task to signal to the manager that the PDF is stale and may need to be regenerated (see TODO #2 for the technician-facing regenerate flow).

### Trigger options to investigate

- **ClickUp webhook `taskUpdated`** — fires when any task field changes; register a new webhook handler (or extend `http_trigger_task_parse`) that checks whether `date_updated` on the task exceeds `snapshot_written_at` in Table Storage
- **On GET in `_handle_task_get`** — compare `clickup_data["date_updated"]` to `entity["snapshot_written_at"]`; if stale, write the flag to ClickUp as a side effect (simpler, but only triggers when a technician scans the QR code)

### Flag mechanism options

1. **Tag** — add a `"pdf-stale"` tag to the task via `POST /api/v2/task/{task_id}/tag/{tag_name}`; visible in ClickUp board/list views; easy to filter on; remove the tag after PDF is regenerated
2. **Custom field** — set a boolean/checkbox "PDF Stale" custom field; more structured but requires the field to exist on the list
3. **Task comment** — post a comment noting the stale PDF; least invasive but adds noise

Recommended starting point: **tag**, since it requires no custom field setup and is trivially reversible.

### Stale detection

- `date_updated` from ClickUp task (`data.get("date_updated")`) is a ms timestamp string — expose this in `_extract_task_fields` (already noted in TODO #2)
- Compare `int(date_updated) > datetime_to_ms(snapshot_written_at)` to determine staleness
- Only flag if a PDF has actually been generated (i.e. `snapshot_written_at` is not null)

### Clearing the flag

- Remove the tag / reset the field after a successful PDF regeneration (TODO #2) or after `http_trigger_task_parse` runs and overwrites the blob

---

## [ ] 10. Use Chinese-appropriate date format when lang is zh

**Where:** `frontend/task-ui/src/utils/dateUtils.ts` (`formatDisplayDate`)

The current `formatDisplayDate` switches locale to `zh-CN` but still uses `hour12: true`, which produces `上午`/`下午` AM/PM markers. Chinese date display conventions prefer a 24-hour clock, and `Intl.DateTimeFormat` with `zh-CN` already renders month names and weekdays in Chinese natively — no manual translation needed.

### Change

Pass locale-specific format options instead of a single shared options object:

```ts
export function formatDisplayDate(iso: string, lang: 'en' | 'zh' = 'en'): string {
  if (!iso) return '—'
  if (lang === 'zh') {
    return new Date(iso).toLocaleString('zh-CN', {
      weekday: 'short',   // 周三
      month: 'short',     // 2月
      day: 'numeric',     // 25日
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,      // 14:00 not 下午2:00
    })
  }
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}
```

`Intl.DateTimeFormat` with `zh-CN` automatically renders weekday and month names in Chinese (e.g. "周三", "2月") — no manual string mapping required.

---

## [ ] 11. Remove property address from translation

**Where:** `function/barcode/shared/pdf/templates.py` (line ~50), `frontend/task-ui/src/hooks/useTaskTranslation.ts`

Property addresses are proper location identifiers and should never be translated — translating them produces garbled or nonsensical output (e.g. "123 Main Street" → "123 大街").

### PDF (`templates.py`)

In `build_header`, `property_address` is currently passed through `translate_fn`:
```python
sanitized_address = self.normalize_address(t(property_address))
```
Change to bypass translation:
```python
sanitized_address = self.normalize_address(property_address)
```

### Frontend (`useTaskTranslation.ts`)

`property_address` is not currently in the `allTexts` translation payload — confirm this stays excluded. `TaskHeader` receives `displayTask` (the translated object), so ensure `property_address` is always taken from the raw `task` and never overwritten by a translation result.

---

## [ ] 12. Add version stamp to generated PDF

**Where:** `function/barcode/shared/pdf/templates.py`, `function/barcode/function_app.py` (`http_trigger_task_parse`)

Print a small version identifier on the PDF so a contractor holding a printed copy can immediately tell whether it is the latest version without scanning the QR code.

### Version identifier

Use `snapshot_written_at` formatted as a short fixed string, e.g.:

```
Generated: 2026-02-25 14:32 UTC
```

This ties directly to the Table Storage `snapshot_written_at` field, so the contractor (or manager) can compare the printed timestamp against the value shown in the UI or ClickUp to confirm they have the current copy.

### Implementation

- Pass `snapshot_written_at` into `MaintenancePDFGenerator.generate()` as a new optional parameter
- Render it as a small footer line on the last page (gray, small font) in `templates.py`
- Do **not** pass it through `translate_fn` — the stamp should always appear in a fixed, unambiguous format

---

## [ ] 13. Write task UI URL back to ClickUp task

**Where:** `function/barcode/function_app.py` (`http_trigger_task_parse`), optionally `_handle_task_get`

After the PDF is generated and the task snapshot is written, post the SWA technician UI URL back to the ClickUp task so managers can navigate directly from ClickUp to the tech-facing form.

### URL format

```
{SWA_BASE_URL}/task/{task_id}
```
`SWA_BASE_URL` is already available as an env var (used by `http_trigger_barcodescan`).

### Delivery options

1. **Task comment** — `POST /api/v2/task/{task_id}/comment` with the URL as the comment body; simplest, no custom field required, always visible in ClickUp activity
2. **Custom field** — store in a "Tech UI Link" URL-type custom field; cleaner but requires the field to exist on the list and the field ID to be known/cached

Recommended: **task comment** for the initial implementation since it requires no ClickUp setup. Can be upgraded to a custom field later.

### Implementation notes

- Add the comment POST in `http_trigger_task_parse` immediately after the blob upload succeeds
- Handle failure non-fatally — log warning, the PDF was already sent so a comment failure should not return a 500
- Avoid duplicate comments on re-generation: consider prefixing with a marker (e.g. `"[Tech UI]"`) so duplicates are obvious, or accept that multiple regenerations will add multiple comments


# 14 CHANGE DATE PCIKER TO BE 24 HRS and TRANSLATED MONTHS