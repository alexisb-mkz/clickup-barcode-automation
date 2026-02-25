import { useState } from 'react'
import { uploadAttachment } from '../api/taskApi'
import type { Task, UploadedAttachment } from '../types/task'

export function useAttachmentUpload(
  taskId: string,
  setTask: React.Dispatch<React.SetStateAction<Task | null>>
) {
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  async function upload(file: File): Promise<UploadedAttachment | null> {
    setUploading(true)
    setUploadError(null)
    try {
      const base64 = await fileToBase64(file)
      const result = await uploadAttachment(taskId, {
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
        data: base64,
      })
      // Optimistically append to local attachment list
      setTask((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          attachments: [
            ...prev.attachments,
            {
              id: result.attachment_id,
              name: result.name,
              url: result.url,
              thumbnail: result.thumbnail,
            },
          ],
        }
      })
      return result
    } catch (err: unknown) {
      const e = err as { response?: { data?: string }; message?: string }
      setUploadError(e?.response?.data ?? e?.message ?? 'Upload failed')
      return null
    } finally {
      setUploading(false)
    }
  }

  return { upload, uploading, uploadError }
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // result is "data:<mime>;base64,<data>" — strip the prefix
      resolve(result.split(',')[1])
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}
