import { useState, useEffect, useRef } from 'react'
import type { Task } from '../types/task'
import type { Lang } from '../contexts/LanguageContext'
import { translateTexts } from '../api/taskApi'

interface TranslationCache {
  cacheKey: string
  translated: Pick<Task, 'task_name' | 'issue_description' | 'tech_notes' | 'action_items'>
}

export function useTaskTranslation(task: Task | null, lang: Lang) {
  const [displayTask, setDisplayTask] = useState<Task | null>(task)
  const [translating, setTranslating] = useState(false)
  const cacheRef = useRef<TranslationCache | null>(null)

  useEffect(() => {
    setDisplayTask(task)

    if (!task || lang !== 'zh') return

    const cacheKey = `${task.task_id}:${task.snapshot_written_at ?? 'none'}`

    // Serve from cache if the task snapshot hasn't changed
    if (cacheRef.current?.cacheKey === cacheKey) {
      setDisplayTask({ ...task, ...cacheRef.current.translated })
      return
    }

    // Build the flat list of strings to translate: [task_name, issue_description, tech_notes, ...item texts]
    const actionTexts = task.action_items.map((item) => item.text)
    const allTexts = [task.task_name, task.issue_description, task.tech_notes, ...actionTexts]

    setTranslating(true)
    translateTexts(allTexts)
      .then((results) => {
        const [translatedName, translatedIssue, translatedTechNotes, ...translatedActionTexts] = results
        const translatedItems = task.action_items.map((item, i) => ({
          ...item,
          text: translatedActionTexts[i] ?? item.text,
        }))

        const translated: Pick<Task, 'task_name' | 'issue_description' | 'tech_notes' | 'action_items'> = {
          task_name: translatedName ?? task.task_name,
          issue_description: translatedIssue ?? task.issue_description,
          tech_notes: translatedTechNotes ?? task.tech_notes,
          action_items: translatedItems,
        }

        cacheRef.current = { cacheKey, translated }
        setDisplayTask({ ...task, ...translated })
      })
      .catch(() => {
        // Fall back to original task on error
      })
      .finally(() => setTranslating(false))
  }, [task, lang])

  return { displayTask, translating }
}
