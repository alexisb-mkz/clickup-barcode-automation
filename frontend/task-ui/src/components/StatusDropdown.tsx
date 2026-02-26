import { STATUS_OPTIONS, getStatusOption } from '../utils/statusMap'
import { useLanguage } from '../contexts/LanguageContext'
import { t } from '../utils/i18n'
import type { Lang } from '../contexts/LanguageContext'

interface Props {
  value: string
  onSave: (uiValue: 'pending' | 'in_progress' | 'completed', clickupValue: string) => void
}

function statusLabel(uiValue: string, lang: Lang): string {
  if (uiValue === 'pending') return t('statusPending', lang)
  if (uiValue === 'in_progress') return t('statusInProgress', lang)
  if (uiValue === 'completed') return t('statusCompleted', lang)
  return uiValue
}

export default function StatusDropdown({ value, onSave }: Props) {
  const { lang } = useLanguage()
  const current = getStatusOption(value)

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const selected = STATUS_OPTIONS.find((s) => s.uiValue === e.target.value)
    if (selected) {
      onSave(selected.uiValue, selected.clickupValue)
    }
  }

  return (
    <div className="px-4 py-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">{t('completionStatus', lang)}</p>
      <div className="flex items-center gap-3">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${current.color}`}>
          {statusLabel(current.uiValue, lang)}
        </span>
        <select
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
          value={current.uiValue}
          onChange={handleChange}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.uiValue} value={opt.uiValue}>
              {statusLabel(opt.uiValue, lang)}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
