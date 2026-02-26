import { useLanguage } from '../contexts/LanguageContext'
import { t } from '../utils/i18n'
import type { Attachment } from '../types/task'

interface Props {
  attachments: Attachment[]
}

export default function AttachmentList({ attachments }: Props) {
  const { lang } = useLanguage()

  if (!attachments || attachments.length === 0) return null

  return (
    <div className="bg-white rounded-xl shadow p-4">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-3">
        {t('attachments', lang)} ({attachments.length})
      </p>
      <div className="grid grid-cols-3 gap-2">
        {attachments.map((a) => (
          <a
            key={a.id}
            href={a.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block rounded-lg overflow-hidden border border-gray-100 hover:border-blue-300 transition-colors"
          >
            {a.thumbnail ? (
              <img
                src={a.thumbnail}
                alt={a.name}
                className="w-full h-20 object-cover"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-20 bg-gray-100 flex items-center justify-center">
                <span className="text-2xl">📄</span>
              </div>
            )}
            <p className="text-xs text-gray-500 truncate px-1.5 py-1">{a.name}</p>
          </a>
        ))}
      </div>
    </div>
  )
}
