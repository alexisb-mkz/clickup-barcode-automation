import axios from 'axios'

const FUNCTION_APP_URL = import.meta.env.VITE_FUNCTION_APP_URL as string

export const apiClient = axios.create({
  baseURL: `${FUNCTION_APP_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
})
