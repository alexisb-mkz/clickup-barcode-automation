import { useState, useEffect, useRef } from 'react'
import { useLanguage } from '../contexts/LanguageContext'
import { t } from '../utils/i18n'

interface Props {
  value: string
  onSave: (notes: string) => void
}

export default function TechNotes({ value, onSave }: Props) {
  const { lang } = useLanguage()
  const [draft, setDraft] = useState(value)
  const focusedRef = useRef(false)

  // Sync draft when value changes externally (e.g. translation arrives or lang toggles),
  // but only if the user isn't actively editing.
  useEffect(() => {
    if (!focusedRef.current) {
      setDraft(value)
    }
  }, [value])

  function handleFocus() {
    focusedRef.current = true
  }

  function handleBlur() {
    focusedRef.current = false
    if (draft !== value) {
      onSave(draft)
    }
  }

  return (
    <div className="px-4 py-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">{t('technicianNotes', lang)}</p>
      <textarea
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
        rows={3}
        placeholder={t('notesPlaceholder', lang)}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onFocus={handleFocus}
        onBlur={handleBlur}
      />
      <p className="text-xs text-gray-400 mt-1">{t('autoSaved', lang)}</p>
    </div>
  )
}
