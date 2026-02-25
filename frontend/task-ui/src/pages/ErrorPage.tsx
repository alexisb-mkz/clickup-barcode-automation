export default function ErrorPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow p-6 max-w-sm w-full text-center">
        <p className="text-red-600 font-semibold text-lg">Something went wrong</p>
        <p className="text-gray-500 text-sm mt-1">Please try scanning the QR code again.</p>
      </div>
    </div>
  )
}
