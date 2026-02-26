import { getPdfUrl } from '../api/taskApi'
import { useLanguage } from '../contexts/LanguageContext'
import { t } from '../utils/i18n'

interface Props {
  taskId: string
}

export default function PdfLink({ taskId }: Props) {
  const { lang } = useLanguage()

  function handleClick() {
    const url = getPdfUrl(taskId)
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  return (
    <button
      onClick={handleClick}
      className="w-full bg-white rounded-xl shadow px-4 py-3 flex items-center gap-3 text-left hover:bg-gray-50 active:bg-gray-100 transition-colors"
    >
      <span className="text-2xl">📄</span>
      <div>
        <p className="text-sm font-medium text-blue-600">{t('viewWorkOrderPdf', lang)}</p>
        <p className="text-xs text-gray-400">{t('opensInNewTab', lang)}</p>
      </div>
    </button>
  )
}
