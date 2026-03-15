import axios from 'axios'

// In production (Railway), frontend and backend are served from the same domain
// Use relative URLs in production, absolute URLs in development
const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL
  if (envUrl) {
    return envUrl
  }
  // In production, use relative URLs (empty string means same origin)
  // In development, use localhost
  if (import.meta.env.PROD) {
    return '' // Empty string = same origin (relative URLs)
  }
  return 'http://localhost:8000'
}

const API_BASE_URL = getApiBaseUrl()

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface ChatRequest {
  query: string
  user_id?: string
  session_id?: string
}

export interface SourceLink {
  title: string
  url: string
  video_url?: string
}

export interface ChatResponse {
  success: boolean
  answer?: string
  error?: string
  documents?: any[]
  model_used?: string
  routing_decision?: any
  processing_time?: number
  source_links?: SourceLink[]
}

export interface ValidationResponse {
  valid: boolean
  errors: string[]
  warnings: string[]
  is_relevant: boolean
  relevance_score?: number
}

export const chatApi = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/api/v1/chat', request)
    return response.data
  },

  validateQuery: async (query: string): Promise<ValidationResponse> => {
    const response = await apiClient.post<ValidationResponse>(
      '/api/v1/chat/validate',
      { query }
    )
    return response.data
  },

  getHealth: async () => {
    const response = await apiClient.get('/api/v1/health')
    return response.data
  },

  getKbUpdateDate: async () => {
    const response = await apiClient.get('/api/v1/health/kb/update-date')
    return response.data
  },
}

