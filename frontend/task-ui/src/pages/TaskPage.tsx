import { useParams } from 'react-router-dom'
import { useTask } from '../hooks/useTask'
import { useTaskUpdate } from '../hooks/useTaskUpdate'
import { useAttachmentUpload } from '../hooks/useAttachmentUpload'
import LoadingSpinner from '../components/LoadingSpinner'
import TaskHeader from '../components/TaskHeader'
import ActionItemList from '../components/ActionItemList'
import ArrivalDatePicker from '../components/ArrivalDatePicker'
import StatusDropdown from '../components/StatusDropdown'
import TechNotes from '../components/TechNotes'
import FileUploader from '../components/FileUploader'
import AttachmentList from '../components/AttachmentList'
import PdfLink from '../components/PdfLink'
import StatusBanner from '../components/StatusBanner'

export default function TaskPage() {
  const { taskId } = useParams<{ taskId: string }>()

  const { task, setTask, loading, error } = useTask(taskId ?? '')
  const { save, saving, saveError, saveSuccess } = useTaskUpdate(taskId ?? '', setTask)
  const { upload, uploading, uploadError } = useAttachmentUpload(taskId ?? '', setTask)

  if (loading) return <LoadingSpinner />

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow p-6 max-w-sm w-full text-center">
          <p className="text-red-600 font-medium">Unable to load task</p>
          <p className="text-gray-500 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  if (!task) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {task.cache_stale && (
          <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm px-4 py-2 rounded-lg">
            Showing cached data — ClickUp may be temporarily unavailable.
          </div>
        )}

        <TaskHeader task={task} />
        <ActionItemList items={task.action_items} />
        <PdfLink taskId={taskId!} />

        <div className="bg-white rounded-xl shadow divide-y divide-gray-100">
          <ArrivalDatePicker
            value={task.arrival_date_iso}
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
