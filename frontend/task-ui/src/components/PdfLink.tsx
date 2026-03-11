import { useState } from 'react'
import { getPdfUrl, regeneratePdf } from '../api/taskApi'
import { useLanguage } from '../contexts/LanguageContext'
import { t, type StringKey } from '../utils/i18n'
import { formatDisplayDate } from '../utils/dateUtils'
import type { Lang } from '../contexts/LanguageContext'

const FIELD_LABEL_KEYS: Record<string, StringKey> = {
  task_name:        'fieldTaskName',
  property_address: 'fieldPropertyAddress',
  issue_description:'fieldIssueDescription',
  action_items:     'fieldActionItems',
  scheduled_date:   'fieldScheduledDate',
}

function fieldLabel(key: string, lang: Lang): string {
  const i18nKey = FIELD_LABEL_KEYS[key]
  return i18nKey ? t(i18nKey, lang) : key
}

interface Props {
  taskId: string
  snapshotWrittenAt: string | null
  pdfStaleFields: string[]
  onRegenerated: (snapshotWrittenAt: string) => void
}

export default function PdfLink({ taskId, snapshotWrittenAt, pdfStaleFields, onRegenerated }: Props) {
  const { lang } = useLanguage()
  const [regenerating, setRegenerating] = useState(false)
  const [regenSuccess, setRegenSuccess] = useState(false)
  const [regenError, setRegenError] = useState<string | null>(null)

  const isStale = pdfStaleFields.length > 0

  function handleViewPdf() {
    window.open(getPdfUrl(taskId), '_blank', 'noopener,noreferrer')
  }

  async function handleRegenerate() {
    setRegenerating(true)
    setRegenError(null)
    setRegenSuccess(false)
    try {
      const result = await regeneratePdf(taskId)
      onRegenerated(result.snapshot_written_at)
      setRegenSuccess(true)
      setTimeout(() => setRegenSuccess(false), 4000)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } }; message?: string }
      setRegenError(e?.response?.data?.error ?? e?.message ?? 'Regeneration failed')
    } finally {
      setRegenerating(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow overflow-hidden">
      {/* View PDF row */}
      <button
        onClick={handleViewPdf}
        className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-gray-50 active:bg-gray-100 transition-colors"
      >
        <span className="text-2xl">📄</span>
        <div>
          <p className="text-sm font-medium text-blue-600">{t('viewWorkOrderPdf', lang)}</p>
          <p className="text-xs text-gray-400">{t('opensInNewTab', lang)}</p>
          {snapshotWrittenAt && (
            <p className="text-xs text-gray-400 mt-0.5">
              {t('pdfGeneratedAt', lang)}: {formatDisplayDate(snapshotWrittenAt, lang)}
            </p>
          )}
        </div>
      </button>

      {/* Stale warning + regenerate */}
      {(isStale || regenSuccess || regenError) && (
        <div className="border-t border-gray-100 px-4 py-3 space-y-2">
          {isStale && !regenSuccess && (
            <div className="text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2">
              <p className="font-medium">⚠ {t('pdfMayBeOutdated', lang)}</p>
              {pdfStaleFields.length > 0 && (
                <ul className="mt-1 ml-3 list-disc space-y-0.5">
                  {pdfStaleFields.map((field) => (
                    <li key={field}>{fieldLabel(field, lang)}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {regenSuccess && (
            <p className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
              {t('pdfRegenerated', lang)}
            </p>
          )}
          {regenError && (
            <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {t('errorPrefix', lang)}: {regenError}
            </p>
          )}
          {(isStale || regenError) && !regenSuccess && (
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="w-full py-2 rounded-lg bg-yellow-500 hover:bg-yellow-600 disabled:opacity-60 text-white text-sm font-medium transition-colors"
            >
              {regenerating ? t('regenerating', lang) : t('regeneratePdf', lang)}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
