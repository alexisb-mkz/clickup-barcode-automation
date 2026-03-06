import { useState, useRef, useEffect } from 'react'

const ZH_MONTHS = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
const ZH_WEEKDAYS = ['日','一','二','三','四','五','六']

interface Props {
  /** Initial value as "YYYY-MM-DDTHH:MM" (local time). May be empty. */
  value: string
  /** Called with the committed "YYYY-MM-DDTHH:MM" string when the user dismisses the picker. */
  onCommit: (value: string) => void
}

export default function ChineseDateTimePicker({ value, onCommit }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  // Parse initial value into parts
  const initDateStr = value ? value.slice(0, 10) : ''
  const initTimeParts = value ? value.slice(11).split(':').map(Number) : [0, 0]
  const initHour = initTimeParts[0] ?? 0
  const initMinute = initTimeParts[1] ?? 0

  const initViewDate = initDateStr ? new Date(initDateStr + 'T12:00:00') : new Date()
  const [viewYear, setViewYear] = useState(initViewDate.getFullYear())
  const [viewMonth, setViewMonth] = useState(initViewDate.getMonth())
  const [selectedDateStr, setSelectedDateStr] = useState(initDateStr)
  const [hour, setHour] = useState(initHour)
  const [minute, setMinute] = useState(initMinute)

  // Keep a ref to the latest assembled value so the mousedown-outside handler
  // always sees the current selection without relying on stale closure state.
  const latestValue = useRef(value)
  useEffect(() => {
    if (selectedDateStr) {
      const hh = String(hour).padStart(2, '0')
      const mm = String(minute).padStart(2, '0')
      latestValue.current = `${selectedDateStr}T${hh}:${mm}`
    }
  }, [selectedDateStr, hour, minute])

  // Commit and close when the user clicks outside the picker.
  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onCommit(latestValue.current)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [onCommit])

  function prevMonth() {
    if (viewMonth === 0) { setViewYear(y => y - 1); setViewMonth(11) }
    else setViewMonth(m => m - 1)
  }

  function nextMonth() {
    if (viewMonth === 11) { setViewYear(y => y + 1); setViewMonth(0) }
    else setViewMonth(m => m + 1)
  }

  function selectDay(day: number) {
    const mm = String(viewMonth + 1).padStart(2, '0')
    const dd = String(day).padStart(2, '0')
    setSelectedDateStr(`${viewYear}-${mm}-${dd}`)
  }

  // Calendar grid
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate()
  const firstDow = new Date(viewYear, viewMonth, 1).getDay()
  const cells: (number | null)[] = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]
  while (cells.length % 7 !== 0) cells.push(null)

  const viewMonthPrefix = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}`
  const selectedDay = selectedDateStr.startsWith(viewMonthPrefix)
    ? parseInt(selectedDateStr.slice(8))
    : null

  const today = new Date()
  const todayDay = today.getFullYear() === viewYear && today.getMonth() === viewMonth
    ? today.getDate()
    : null

  const inputCls = 'border border-gray-300 rounded px-1 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 text-center'

  return (
    <div ref={ref} className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 w-60 select-none">

      {/* Month navigation */}
      <div className="flex items-center justify-between mb-2">
        <button
          type="button"
          onClick={prevMonth}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-gray-100 text-gray-500 text-base"
        >‹</button>
        <span className="text-sm font-semibold text-gray-800">
          {viewYear}年{ZH_MONTHS[viewMonth]}
        </span>
        <button
          type="button"
          onClick={nextMonth}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-gray-100 text-gray-500 text-base"
        >›</button>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-1">
        {ZH_WEEKDAYS.map(d => (
          <div key={d} className="text-center text-xs text-gray-400 py-0.5 font-medium">{d}</div>
        ))}
      </div>

      {/* Day grid */}
      <div className="grid grid-cols-7">
        {cells.map((day, i) => (
          <div key={i} className="flex items-center justify-center h-8">
            {day !== null && (
              <button
                type="button"
                onClick={() => selectDay(day)}
                className={`w-7 h-7 rounded-full text-xs transition-colors ${
                  selectedDay === day
                    ? 'bg-blue-500 text-white font-medium'
                    : todayDay === day
                    ? 'bg-blue-50 text-blue-600 font-medium'
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                {day}
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Time selectors — guaranteed 24hr via <select> */}
      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-1.5">
        <span className="text-xs text-gray-500 shrink-0">时间</span>
        <select
          value={hour}
          onChange={(e) => setHour(parseInt(e.target.value))}
          className={`${inputCls} w-14`}
        >
          {Array.from({ length: 24 }, (_, h) => (
            <option key={h} value={h}>{String(h).padStart(2, '0')}</option>
          ))}
        </select>
        <span className="text-gray-400 font-medium text-sm">:</span>
        <select
          value={minute}
          onChange={(e) => setMinute(parseInt(e.target.value))}
          className={`${inputCls} w-14`}
        >
          {Array.from({ length: 60 }, (_, m) => (
            <option key={m} value={m}>{String(m).padStart(2, '0')}</option>
          ))}
        </select>
      </div>

      {/* Action buttons */}
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => onCommit('')}
          className="flex-1 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-50 text-gray-600 text-sm transition-colors"
        >
          清除
        </button>
        <button
          type="button"
          onClick={() => onCommit(latestValue.current)}
          className="flex-1 py-1.5 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium transition-colors"
        >
          确认
        </button>
      </div>
    </div>
  )
}
