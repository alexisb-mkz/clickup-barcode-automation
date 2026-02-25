export interface StatusOption {
  label: string
  uiValue: 'pending' | 'in_progress' | 'completed'
  clickupValue: string
  color: string
}

// Update clickupValue strings to match the exact status names in your ClickUp workspace.
// You can find these by inspecting task_status in the GET /api/task/{id} response.
export const STATUS_OPTIONS: StatusOption[] = [
  {
    label: 'Pending',
    uiValue: 'pending',
    clickupValue: 'open',
    color: 'bg-gray-100 text-gray-700',
  },
  {
    label: 'In Progress',
    uiValue: 'in_progress',
    clickupValue: 'in progress',
    color: 'bg-yellow-100 text-yellow-800',
  },
  {
    label: 'Completed',
    uiValue: 'completed',
    clickupValue: 'complete',
    color: 'bg-green-100 text-green-800',
  },
]

export function getStatusOption(uiValue: string): StatusOption {
  return STATUS_OPTIONS.find((s) => s.uiValue === uiValue) ?? STATUS_OPTIONS[0]
}
