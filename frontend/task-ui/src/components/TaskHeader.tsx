import type { Task } from '../types/task'

interface Props {
  task: Task
}

export default function TaskHeader({ task }: Props) {
  return (
    <div className="bg-white rounded-xl shadow p-4 space-y-1">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">Maintenance Task</p>
      <h1 className="text-xl font-bold text-gray-900 leading-tight">{task.property_address || task.task_name}</h1>
      {task.property_address && task.task_name && (
        <p className="text-sm text-gray-500">{task.task_name}</p>
      )}
      {task.issue_description && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">Issue</p>
          <p className="text-sm text-gray-700">{task.issue_description}</p>
        </div>
      )}
      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-100">
        <span className="text-xs text-gray-400">ClickUp status:</span>
        <span className="text-xs font-medium text-gray-600 capitalize">{task.task_status || '—'}</span>
      </div>
    </div>
  )
}
