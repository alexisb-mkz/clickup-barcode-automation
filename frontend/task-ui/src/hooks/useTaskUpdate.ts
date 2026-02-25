import { useState } from 'react'
import { updateTask } from '../api/taskApi'
import type { Task, TaskUpdatePayload } from '../types/task'

export function useTaskUpdate(taskId: string, setTask: React.Dispatch<React.SetStateAction<Task | null>>) {
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  async function save(payload: TaskUpdatePayload) {
    setSaving(true)
    setSaveError(null)
    setSaveSuccess(false)
    try {
      const updated = await updateTask(taskId, payload)
      setTask((prev) => prev ? { ...prev, ...updated } : prev)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2500)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } }; message?: string }
      setSaveError(e?.response?.data?.error ?? e?.message ?? 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return { save, saving, saveError, saveSuccess }
}
