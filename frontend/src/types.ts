export type DocumentStatus = 'uploaded' | 'processing' | 'processed' | 'failed'

export interface DocumentRecord {
  document_id: string
  filename: string
  status: DocumentStatus
  metadata: Record<string, unknown>
}

export interface UploadResponse {
  success: boolean
  document_id: string
  filename: string
  message: string
}

export interface ProcessResponse {
  success: boolean
  document_id: string
  message: string
  results: {
    sections: number
    chunks: number
    completeness_score: number
    quality_score: number
    risk_score: number
    risk_level: string
  }
}

export interface AnalysisEnvelope {
  document_id: string
  data: Record<string, any>
}

export interface Source {
  chunk_id: string
  section_id: string
  section_title: string
  similarity: number
}

export interface QueryResponse {
  success: boolean
  document_id: string
  question: string
  answer: string
  sources: Source[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

export type AnalysisKind = 'completeness' | 'quality' | 'features' | 'risk'
