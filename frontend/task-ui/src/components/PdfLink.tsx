import { getPdfUrl } from '../api/taskApi'

interface Props {
  taskId: string
}

export default function PdfLink({ taskId }: Props) {
  function handleClick() {
    const url = getPdfUrl(taskId)
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  return (
    <button
      onClick={handleClick}
      className="w-full bg-white rounded-xl shadow px-4 py-3 flex items-center gap-3 text-left hover:bg-gray-50 active:bg-gray-100 transition-colors"
    >
      <span className="text-2xl">📄</span>
      <div>
        <p className="text-sm font-medium text-blue-600">View Work Order PDF</p>
        <p className="text-xs text-gray-400">Opens in new tab</p>
      </div>
    </button>
  )
}
