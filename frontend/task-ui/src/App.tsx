import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import TaskPage from './pages/TaskPage'
import NotFoundPage from './pages/NotFoundPage'
import ErrorPage from './pages/ErrorPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/task/:taskId" element={<TaskPage />} />
        <Route path="/error" element={<ErrorPage />} />
        <Route path="/404" element={<NotFoundPage />} />
        <Route path="/" element={<Navigate to="/404" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}
