import { useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useTask } from '../hooks/useTask'
import { useTaskUpdate } from '../hooks/useTaskUpdate'
import { useAttachmentUpload } from '../hooks/useAttachmentUpload'
import { useTaskTranslation } from '../hooks/useTaskTranslation'
import { useLanguage, hasStoredLangPreference } from '../contexts/LanguageContext'
import { t } from '../utils/i18n'
import { msTimestampToDate } from '../utils/dateUtils'
import LoadingSpinner from '../components/LoadingSpinner'
import TaskHeader from '../components/TaskHeader'
import ActionItemList from '../components/ActionItemList'
import ArrivalDatePicker from '../components/ArrivalDatePicker'
import StatusDropdown from '../components/StatusDropdown'
import TechNotes from '../components/TechNotes'
import FileUploader from '../components/FileUploader'
import AttachmentList from '../components/AttachmentList'
import PdfLink from '../components/PdfLink'
import ScheduledWindow from '../components/ScheduledWindow'
import StatusBanner from '../components/StatusBanner'

export default function TaskPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const { lang, toggleLang, setLangAuto } = useLanguage()
  const langInitialized = useRef(false)

  const { task, setTask, loading, error } = useTask(taskId ?? '')
  const { displayTask, translating } = useTaskTranslation(task, lang)
  const { save, saving, saveError, saveSuccess } = useTaskUpdate(taskId ?? '', setTask)
  const { upload, uploading, uploadError } = useAttachmentUpload(taskId ?? '', setTask)

  // Auto-default to Chinese if translate_flag is set and user has no stored preference.
  // Uses setLangAuto so it does NOT write to localStorage — only explicit toggle() persists.
  useEffect(() => {
    if (task && !langInitialized.current) {
      langInitialized.current = true
      if (task.translate_flag && !hasStoredLangPreference()) {
        setLangAuto('zh')
      }
    }
  }, [task, setLangAuto])

  if (loading) return <LoadingSpinner />

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow p-6 max-w-sm w-full text-center">
          <p className="text-red-600 font-medium">{t('unableToLoad', lang)}</p>
          <p className="text-gray-500 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  if (!task || !displayTask) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">

        {/* Language toggle */}
        <div className="flex justify-end items-center gap-3">
          {translating && (
            <span className="text-xs text-gray-400">{t('translating', lang)}</span>
          )}
          <button
            onClick={toggleLang}
            className="text-sm px-3 py-1 rounded-full border border-gray-200 bg-white shadow-sm hover:bg-gray-50 transition-colors"
          >
            <span className={lang === 'en' ? 'font-semibold text-gray-900' : 'text-gray-400'}>EN</span>
            <span className="mx-1.5 text-gray-300">|</span>
            <span className={lang === 'zh' ? 'font-semibold text-gray-900' : 'text-gray-400'}>中文</span>
          </button>
        </div>

        {task.cache_stale && (
          <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm px-4 py-2 rounded-lg">
            {t('cachedData', lang)}
          </div>
        )}

        <TaskHeader task={displayTask} />
        <ActionItemList items={displayTask.action_items} />
        <PdfLink taskId={taskId!} />

        <div className="bg-white rounded-xl shadow divide-y divide-gray-100">
          <ScheduledWindow
            startDateMs={task.start_date_ms}
            bufferHours={task.start_buffer_hours}
          />
          <ArrivalDatePicker
            value={task.arrival_date_iso || (msTimestampToDate(task.start_date_ms)?.toISOString() ?? '')}
            onSave={(iso) => save({ arrival_date_iso: iso })}
          />
          <StatusDropdown
            value={task.completion_status}
            onSave={(uiValue, clickupValue) =>
              save({ completion_status: uiValue, clickup_status: clickupValue })
            }
          />
          <TechNotes
            value={task.tech_notes}
            onSave={(notes) => save({ tech_notes: notes })}
          />
        </div>

        <FileUploader onUpload={upload} uploading={uploading} uploadError={uploadError} />
        <AttachmentList attachments={task.attachments} />

        <StatusBanner saving={saving} saveSuccess={saveSuccess} saveError={saveError} />
      </div>
    </div>
  )
}
