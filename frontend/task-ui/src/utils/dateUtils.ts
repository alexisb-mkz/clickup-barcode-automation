export function isoToDatetimeLocal(iso: string): string {
  if (!iso) return ''
  // datetime-local inputs expect "YYYY-MM-DDTHH:MM" in LOCAL time.
  // Slicing the UTC ISO string directly would show the wrong time in non-UTC timezones.
  const d = new Date(iso)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}T${hh}:${min}`
}

export function datetimeLocalToIso(value: string): string {
  if (!value) return ''
  return new Date(value).toISOString()
}

export function formatDisplayDate(iso: string, lang: 'en' | 'zh' = 'en'): string {
  if (!iso) return '—'
  const locale = lang === 'zh' ? 'zh-CN' : 'en-US'
  return new Date(iso).toLocaleString(locale, {
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
