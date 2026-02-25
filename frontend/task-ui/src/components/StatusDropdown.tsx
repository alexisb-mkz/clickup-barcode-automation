import { STATUS_OPTIONS, getStatusOption } from '../utils/statusMap'

interface Props {
  value: string
  onSave: (uiValue: 'pending' | 'in_progress' | 'completed', clickupValue: string) => void
}

export default function StatusDropdown({ value, onSave }: Props) {
  const current = getStatusOption(value)

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const selected = STATUS_OPTIONS.find((s) => s.uiValue === e.target.value)
    if (selected) {
      onSave(selected.uiValue, selected.clickupValue)
    }
  }

  return (
    <div className="px-4 py-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">Completion Status</p>
      <div className="flex items-center gap-3">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${current.color}`}>
          {current.label}
        </span>
        <select
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
          value={current.uiValue}
          onChange={handleChange}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.uiValue} value={opt.uiValue}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
