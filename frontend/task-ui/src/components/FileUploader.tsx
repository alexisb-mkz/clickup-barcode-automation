import { useRef } from 'react'

interface Props {
  onUpload: (file: File) => Promise<unknown>
  uploading: boolean
  uploadError: string | null
}

export default function FileUploader({ onUpload, uploading, uploadError }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    for (const file of Array.from(files)) {
      await onUpload(file)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div className="space-y-2">
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className="bg-white rounded-xl shadow border-2 border-dashed border-gray-200 px-4 py-6 text-center cursor-pointer hover:border-blue-300 hover:bg-blue-50 transition-colors"
      >
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-500">Uploading...</p>
          </div>
        ) : (
          <>
            <p className="text-3xl mb-1">📎</p>
            <p className="text-sm font-medium text-gray-700">Tap to attach a photo or file</p>
            <p className="text-xs text-gray-400 mt-0.5">or drag and drop</p>
          </>
        )}
      </div>
      {uploadError && (
        <p className="text-xs text-red-500 px-1">{uploadError}</p>
      )}
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/*,application/pdf,.doc,.docx"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  )
}
