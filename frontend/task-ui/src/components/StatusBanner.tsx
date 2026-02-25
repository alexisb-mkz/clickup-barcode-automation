interface Props {
  saving: boolean
  saveSuccess: boolean
  saveError: string | null
}

export default function StatusBanner({ saving, saveSuccess, saveError }: Props) {
  if (!saving && !saveSuccess && !saveError) return null

  return (
    <div
      className={`fixed bottom-4 left-1/2 -translate-x-1/2 px-5 py-2.5 rounded-full shadow-lg text-sm font-medium text-white transition-all ${
        saveError
          ? 'bg-red-500'
          : saveSuccess
          ? 'bg-green-500'
          : 'bg-blue-500'
      }`}
    >
      {saveError ? `Error: ${saveError}` : saveSuccess ? '✓ Saved' : 'Saving...'}
    </div>
  )
}
