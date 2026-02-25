import { apiClient } from './client'
import type { Task, TaskUpdatePayload, AttachmentUploadPayload, UploadedAttachment } from '../types/task'

export async function getTask(taskId: string): Promise<Task> {
  const { data } = await apiClient.get<Task>(`/task/${taskId}`)
  return data
}

export async function updateTask(taskId: string, payload: TaskUpdatePayload): Promise<Partial<Task>> {
  const { data } = await apiClient.put<Partial<Task>>(`/task/${taskId}`, payload)
  return data
}

export async function uploadAttachment(
  taskId: string,
  payload: AttachmentUploadPayload
): Promise<UploadedAttachment> {
  const { data } = await apiClient.post<UploadedAttachment>(`/task/${taskId}/attachment`, payload)
  return data
}

export async function getPdfUrl(taskId: string): Promise<string> {
  // Returns the PDF directly — open the URL in a new tab
  return `${import.meta.env.VITE_FUNCTION_APP_URL}/api/task/${taskId}/pdf`
}
