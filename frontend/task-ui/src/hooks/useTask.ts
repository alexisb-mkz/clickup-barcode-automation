import { useState, useEffect } from 'react'
import { getTask } from '../api/taskApi'
import type { Task } from '../types/task'

export function useTask(taskId: string) {
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!taskId) return
    setLoading(true)
    setError(null)
    getTask(taskId)
      .then(setTask)
      .catch((err) => {
        const msg = err?.response?.data?.error ?? err?.message ?? 'Failed to load task'
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [taskId])

  return { task, setTask, loading, error }
}
