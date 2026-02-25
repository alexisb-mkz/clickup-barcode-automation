export interface ActionItem {
  text: string
  type: 'bullet' | 'ordered' | null
}

export interface Attachment {
  id: string
  name: string
  url: string
  thumbnail: string | null
}

export interface Task {
  task_id: string
  task_name: string
  property_address: string
  issue_description: string
  action_items: ActionItem[]
  start_date_ms: string
  start_buffer_hours: number
  task_status: string
  translate_flag: boolean
  attachments: Attachment[]
  // Tech-writable fields (stored in Table Storage)
  arrival_date_iso: string
  completion_status: 'pending' | 'in_progress' | 'completed'
  tech_notes: string
  last_ui_update_at: string | null
  snapshot_written_at: string | null
  cache_stale: boolean
}

export interface TaskUpdatePayload {
  arrival_date_iso?: string
  completion_status?: string
  tech_notes?: string
  clickup_status?: string
}

export interface AttachmentUploadPayload {
  filename: string
  content_type: string
  data: string // base64
}

export interface UploadedAttachment {
  attachment_id: string
  name: string
  url: string
  thumbnail: string | null
}
