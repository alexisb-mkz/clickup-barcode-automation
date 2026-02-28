import { useState, useEffect } from 'react'
import { useLanguage } from '../contexts/LanguageContext'
import { t } from '../utils/i18n'
import { formatDisplayDate, msTimestampToDate, isoToDatetimeLocal } from '../utils/dateUtils'

interface Props {
  startDateMs: string
  bufferHours: number
  onSave: (iso: string) => void
}

export default function ScheduledWindow({ startDateMs, bufferHours, onSave }: Props) {
  const { lang } = useLanguage()

  const startIso = msTimestampToDate(startDateMs)?.toISOString() ?? ''

  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(isoToDatetimeLocal(startIso))

  // Keep draft in sync when startDateMs changes externally (e.g. optimistic update after save,
  // or fresh data from ClickUp on reload), but only when not actively editing.
  useEffect(() => {
    if (!editing) {
      setDraft(isoToDatetimeLocal(startIso))
    }
  }, [startIso, editing])

  // Calculate end date from current draft while editing, otherwise from startIso.
  const baseDate = (() => {
    if (editing && draft) {
      const d = new Date(draft)
      return isNaN(d.getTime()) ? null : d
    }
    return startIso ? new Date(startIso) : null
  })()

  const endDate = baseDate && bufferHours > 0
    ? new Date(baseDate.getTime() + bufferHours * 60 * 60 * 1000)
    : null

  function handleBlur() {
    setEditing(false)
    if (draft) {
      onSave(new Date(draft).toISOString())
    }
  }

  return (
    <div className="px-4 py-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">
        {t('scheduledWindow', lang)}
        {bufferHours > 0 && (
          <span className="ml-1.5 normal-case text-gray-300">
            (±{bufferHours} {t('hrBuffer', lang)})
          </span>
        )}
      </p>
      <div className="flex items-center flex-wrap gap-x-1.5 gap-y-1">
        {editing ? (
          <input
            type="datetime-local"
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={handleBlur}
            autoFocus
          />
        ) : (
          <button
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 bg-gray-50 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors text-sm text-gray-800"
            onClick={() => { setDraft(isoToDatetimeLocal(startIso)); setEditing(true) }}
          >
            <svg className="w-3.5 h-3.5 text-gray-400 shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5.75 2a.75.75 0 0 1 .75.75V4h7V2.75a.75.75 0 0 1 1.5 0V4h.25A2.75 2.75 0 0 1 18 6.75v8.5A2.75 2.75 0 0 1 15.25 18H4.75A2.75 2.75 0 0 1 2 15.25v-8.5A2.75 2.75 0 0 1 4.75 4H5V2.75A.75.75 0 0 1 5.75 2Zm-1 5.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h10.5c.69 0 1.25-.56 1.25-1.25v-6.5c0-.69-.56-1.25-1.25-1.25H4.75Z" clipRule="evenodd" />
            </svg>
            {startIso
              ? formatDisplayDate(startIso, lang)
              : <span className="text-gray-400">{t('tapToSetArrival', lang)}</span>
            }
          </button>
        )}
        {endDate && (
          <>
            <span className="text-sm text-gray-400">{t('to', lang)}</span>
            <span className="text-sm text-gray-800">{formatDisplayDate(endDate.toISOString(), lang)}</span>
          </>
        )}
      </div>
    </div>
  )
}
