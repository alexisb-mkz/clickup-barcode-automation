import { useState } from 'react'

interface Props {
  value: string
  onSave: (notes: string) => void
}

export default function TechNotes({ value, onSave }: Props) {
  const [draft, setDraft] = useState(value)

  function handleBlur() {
    if (draft !== value) {
      onSave(draft)
    }
  }

  return (
    <div className="px-4 py-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">Technician Notes</p>
      <textarea
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
        rows={3}
        placeholder="Add notes about this task..."
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={handleBlur}
      />
      <p className="text-xs text-gray-400 mt-1">Auto-saved when you leave this field</p>
    </div>
  )
}
