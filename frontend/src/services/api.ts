import type {
  AnalysisEnvelope,
  AuthUser,
  DocumentRecord,
  LoginResponse,
  ProcessResponse,
  QueryResponse,
  RegisterResponse,
  UploadResponse,
} from '../types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const AUTH_STORAGE_KEY = 'dpr_auth_session'

export function readStoredSession() {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY)
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as { token: string; user: AuthUser }
    return parsed.token ? parsed : null
  } catch {
    return null
  }
}

export function persistSession(session: { token: string; user: AuthUser } | null) {
  if (!session) {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    return
  }
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session))
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const session = readStoredSession()
  const headers = new Headers(init?.headers)
  if (session?.token) headers.set('Authorization', `Bearer ${session.token}`)

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (body.detail) detail = body.detail
    } catch {
      // Keep the HTTP status when the backend did not return JSON.
    }
    throw new Error(detail)
  }

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) return response.json() as Promise<T>
  return undefined as T
}

export async function registerUser(payload: { name: string; email: string; password: string }) {
  return request<RegisterResponse>('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function loginUser(payload: { email: string; password: string }) {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function healthCheck() {
  return request<{ status: string; service: string }>('/health')
}

export async function getDocuments() {
  return request<{ documents: DocumentRecord[] }>('/documents')
}

export async function getDocument(documentId: string) {
  return request<DocumentRecord>(`/documents/${documentId}`)
}

export async function uploadDocument(file: File) {
  const form = new FormData()
  form.append('file', file)
  return request<UploadResponse>('/documents/upload', { method: 'POST', body: form })
}

export async function processDocument(documentId: string) {
  return request<ProcessResponse>(`/documents/${documentId}/process`, { method: 'POST' })
}

export async function getAnalysis(documentId: string, kind: 'completeness' | 'quality' | 'features' | 'risk') {
  return request<AnalysisEnvelope>(`/analysis/${documentId}/${kind}`)
}

export async function getCompleteAnalysis(documentId: string) {
  return request<{
    document_id: string
    completeness: Record<string, any>
    quality: Record<string, any>
    features: Record<string, any>
    risk: Record<string, any>
  }>(`/analysis/${documentId}`)
}

export async function askQuestion(documentId: string, question: string, topK = 5) {
  return request<QueryResponse>('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, question, top_k: topK }),
  })
}
