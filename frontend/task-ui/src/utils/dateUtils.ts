export function isoToDatetimeLocal(iso: string): string {
  if (!iso) return ''
  // Strip timezone for datetime-local input (expects "YYYY-MM-DDTHH:MM")
  return iso.slice(0, 16)
}

export function datetimeLocalToIso(value: string): string {
  if (!value) return ''
  return new Date(value).toISOString()
}

export function formatDisplayDate(iso: string): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

export function msTimestampToDate(ms: string): Date | null {
  const n = parseInt(ms)
  if (isNaN(n)) return null
  return new Date(n)
}
