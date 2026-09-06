import type {
  AnalysisEnvelope,
  DocumentRecord,
  ProcessResponse,
  QueryResponse,
  UploadResponse,
} from '../types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init)
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
  return response.json() as Promise<T>
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
