import { useState } from 'react'
import { isoToDatetimeLocal, formatDisplayDate } from '../utils/dateUtils'

interface Props {
  value: string
  onSave: (iso: string) => void
}

export default function ArrivalDatePicker({ value, onSave }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(isoToDatetimeLocal(value))

  function handleBlur() {
    setEditing(false)
    if (draft) {
      onSave(new Date(draft).toISOString())
    }
  }

  return (
    <div className="px-4 py-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">Arrival Date & Time</p>
      {editing ? (
        <input
          type="datetime-local"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={handleBlur}
          autoFocus
        />
      ) : (
        <button
          className="w-full text-left"
          onClick={() => {
            setDraft(isoToDatetimeLocal(value))
            setEditing(true)
          }}
        >
          <p className="text-sm text-gray-800">
            {value ? formatDisplayDate(value) : <span className="text-gray-400">Tap to set arrival time</span>}
          </p>
        </button>
      )}
    </div>
  )
}
