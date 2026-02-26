import { useLanguage } from '../contexts/LanguageContext'
import { t } from '../utils/i18n'
import { formatDisplayDate, msTimestampToDate } from '../utils/dateUtils'

interface Props {
  startDateMs: string
  bufferHours: number
}

export default function ScheduledWindow({ startDateMs, bufferHours }: Props) {
  const { lang } = useLanguage()

  const startDate = msTimestampToDate(startDateMs)
  if (!startDate) return null

  const endDate = bufferHours > 0
    ? new Date(startDate.getTime() + bufferHours * 60 * 60 * 1000)
    : null

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
      <p className="text-sm text-gray-800">
        {formatDisplayDate(startDate.toISOString())}
        {endDate && (
          <>
            <span className="mx-1.5 text-gray-400">{t('to', lang)}</span>
            {formatDisplayDate(endDate.toISOString())}
          </>
        )}
      </p>
    </div>
  )
}
