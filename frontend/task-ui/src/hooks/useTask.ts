import { useState, useEffect, useRef } from 'react'
import { getTask } from '../api/taskApi'
import type { Task } from '../types/task'

const POLL_INTERVAL_MS = 30_000

export function useTask(taskId: string) {
  const [task, setTask] = useState<Task | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const taskRef = useRef<Task | null>(null)
  taskRef.current = task

  function refresh() {
    if (!taskId) return
    getTask(taskId)
      .then(setTask)
      .catch(() => {
        // Silent — keep showing the last good data if a manual refresh fails
      })
  }

  // Initial load
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

  // Background poll — only when tab is visible and initial load has succeeded
  useEffect(() => {
    if (!taskId) return

    let timerId: ReturnType<typeof setTimeout>

    function scheduleNext() {
      timerId = setTimeout(async () => {
        if (document.visibilityState === 'hidden' || !taskRef.current) {
          scheduleNext()
          return
        }
        try {
          const fresh = await getTask(taskId)
          setTask(fresh)
        } catch {
          // Poll failures are silent — the user still has the last good data
        }
        scheduleNext()
      }, POLL_INTERVAL_MS)
    }

    scheduleNext()
    return () => clearTimeout(timerId)
  }, [taskId])

  return { task, setTask, refresh, loading, error }
}
