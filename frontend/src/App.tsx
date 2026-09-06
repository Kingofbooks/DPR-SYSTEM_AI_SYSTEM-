import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import {
  AlertCircle, ArrowUpRight, BarChart3, Bot, Check, ChevronDown, CircleHelp,
  FileText, Gauge, Layers3, LoaderCircle, MessageSquare, Paperclip, PanelRight,
  RefreshCw, Send, ShieldCheck, Sparkles, UploadCloud, X, Zap,
} from 'lucide-react'
import {
  askQuestion, getAnalysis, getCompleteAnalysis, getDocument, getDocuments,
  healthCheck, processDocument, uploadDocument,
} from './services/api'
import type { AnalysisKind, AnalysisEnvelope, ChatMessage, DocumentRecord, ProcessResponse, Source } from './types'
import { normalizeCompleteness, normalizeQuality, normalizeRisk, percentageText, safeNumber, toPercentage } from './utils/analysis'
import './styles.css'

const pipelineSteps = [
  ['PDF Reading', 'Extracting text and content from the document.'],
  ['TOC Detection', 'Detecting document structure.'],
  ['TOC Parsing', 'Identifying document sections.'],
  ['Section Mapping', 'Locating sections inside the document.'],
  ['Section Extraction', 'Extracting section content.'],
  ['Document Chunking', 'Breaking content into semantic chunks.'],
  ['Embedding Generation', 'Creating vectors for retrieval.'],
  ['Completeness Assessment', 'Checking important DPR sections.'],
  ['Quality Assessment', 'Evaluating extracted sections.'],
  ['Feature Construction', 'Combining analysis results into features.'],
  ['Risk Assessment', 'Calculating the overall DPR risk score.'],
] as const

const suggestions = ['What is the proposed road alignment?', 'What are the major risks?', 'Is land acquisition discussed?', 'What is the pavement design?']

function scorePercent(value: unknown) { return toPercentage(value) ?? 0 }

function formatLabel(key: string) {
  return key.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedDocument, setSelectedDocument] = useState<DocumentRecord | null>(null)
  const [analysis, setAnalysis] = useState<Record<AnalysisKind, Record<string, any>>>({ completeness: {}, quality: {}, features: {}, risk: {} })
  const [processingResults, setProcessingResults] = useState<ProcessResponse['results'] | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [page, setPage] = useState<'documents' | 'analysis' | 'completeness' | 'quality' | 'features' | 'risk'>('documents')
  const [apiOnline, setApiOnline] = useState(false)
  const [busy, setBusy] = useState(false)
  const [stage, setStage] = useState<'idle' | 'uploading' | 'processing' | 'complete' | 'failed'>('idle')
  const [error, setError] = useState('')
  const [chatOpen, setChatOpen] = useState(true)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const [chatBusy, setChatBusy] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const selected = useMemo(() => documents.find((document) => document.document_id === selectedId) || selectedDocument, [documents, selectedDocument, selectedId])

  useEffect(() => {
    healthCheck().then(() => setApiOnline(true)).catch(() => setApiOnline(false))
    getDocuments().then((response) => setDocuments(response.documents)).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!selectedId) return
    const document = documents.find((item) => item.document_id === selectedId)
    if (document) setSelectedDocument(document)
    if (document?.status === 'processed') loadAnalysis(selectedId)
  }, [selectedId, documents])

  async function loadAnalysis(documentId: string) {
    try {
      const response = await getCompleteAnalysis(documentId)
      setAnalysis({ completeness: normalizeCompleteness(response.completeness), quality: normalizeQuality(response.quality), features: response.features || {}, risk: normalizeRisk(response.risk) })
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Analysis is not available yet.')
    }
  }

  function acceptFile(candidate?: File) {
    if (!candidate) return
    if (candidate.type !== 'application/pdf' && !candidate.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are allowed.')
      return
    }
    setError('')
    setFile(candidate)
  }

  async function uploadAndProcess() {
    if (!file) return
    setBusy(true)
    setError('')
    try {
      setStage('uploading')
      const uploaded = await uploadDocument(file)
      setSelectedId(uploaded.document_id)
      setStage('processing')
      const processed = await processDocument(uploaded.document_id)
      setProcessingResults(processed.results)
      setStage('complete')
      const refreshed = await getDocuments()
      setDocuments(refreshed.documents)
      setSelectedDocument(await getDocument(uploaded.document_id))
      await loadAnalysis(uploaded.document_id)
      setPage('analysis')
    } catch (uploadError) {
      setStage('failed')
      setError(uploadError instanceof Error ? uploadError.message : 'Unable to process this document.')
    } finally {
      setBusy(false)
    }
  }

  async function selectDocument(document: DocumentRecord) {
    setSelectedId(document.document_id)
    setSelectedDocument(document)
    setProcessingResults(null)
    setError('')
    if (document.status === 'processed') {
      await loadAnalysis(document.document_id)
      setPage('analysis')
    } else {
      setPage('documents')
    }
  }

  async function reprocess() {
    if (!selected) return
    setBusy(true)
    setStage('processing')
    setError('')
    try {
      const response = await processDocument(selected.document_id)
      setProcessingResults(response.results)
      setStage('complete')
      await loadAnalysis(selected.document_id)
      const refreshed = await getDocuments()
      setDocuments(refreshed.documents)
      setPage('analysis')
    } catch (processError) {
      setStage('failed')
      setError(processError instanceof Error ? processError.message : 'Processing failed.')
    } finally {
      setBusy(false)
    }
  }

  async function submitQuestion(text = question) {
    const cleaned = text.trim()
    if (!cleaned || !selected) return
    setQuestion('')
    setChatBusy(true)
    setMessages((current) => [...current, { role: 'user', content: cleaned }])
    try {
      const response = await askQuestion(selected.document_id, cleaned)
      setMessages((current) => [...current, { role: 'assistant', content: response.answer, sources: response.sources }])
    } catch (queryError) {
      setMessages((current) => [...current, { role: 'assistant', content: queryError instanceof Error ? queryError.message : 'Unable to answer right now.' }])
    } finally {
      setChatBusy(false)
    }
  }

  const processed = selected?.status === 'processed'
  const risk = normalizeRisk(analysis.risk)
  const completeness = normalizeCompleteness(analysis.completeness)
  const quality = normalizeQuality(analysis.quality)
  const features = analysis.features.features || {}
  const sections = quality.sections || []
  const summary = completeness.summary || {}
  const completenessScores = completeness.scores || {}
  const pageTitle = page === 'documents' ? 'Document workspace' : page === 'analysis' ? 'Analysis overview' : `${formatLabel(page)} analysis`

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Sparkles size={18} /></div><div><strong>DPR AI SYSTEM</strong><span>Document intelligence</span></div></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="nav-list">
          <NavButton active={page === 'documents'} icon={<FileText size={17} />} label="Documents" onClick={() => setPage('documents')} />
          <NavButton active={page === 'analysis'} icon={<BarChart3 size={17} />} label="Analysis dashboard" onClick={() => setPage('analysis')} disabled={!processed} />
          <NavButton active={page === 'completeness'} icon={<Layers3 size={17} />} label="Completeness" onClick={() => setPage('completeness')} disabled={!processed} />
          <NavButton active={page === 'quality'} icon={<Gauge size={17} />} label="Quality" onClick={() => setPage('quality')} disabled={!processed} />
          <NavButton active={page === 'features'} icon={<Zap size={17} />} label="Feature profile" onClick={() => setPage('features')} disabled={!processed} />
          <NavButton active={page === 'risk'} icon={<ShieldCheck size={17} />} label="Risk assessment" onClick={() => setPage('risk')} disabled={!processed} />
        </nav>
        <div className="sidebar-bottom"><div className={`connection ${apiOnline ? 'online' : ''}`}><span className="status-dot" />{apiOnline ? 'System online' : 'Backend offline'}</div><span className="version">API v1.0</span></div>
      </aside>

      <main className="main-area">
        <header className="topbar"><div><div className="eyebrow">DPR INTELLIGENCE PLATFORM</div><h1>{pageTitle}</h1></div><div className="topbar-actions">{selected && <div className="context-pill"><FileText size={15} /><span>{selected.filename}</span><b>{selected.status}</b></div>}<button className="icon-button" title="Open assistant" onClick={() => setChatOpen((open) => !open)}><PanelRight size={18} /></button></div></header>
        {error && <div className="error-banner"><AlertCircle size={17} /><span>{error}</span><button onClick={() => setError('')}><X size={15} /></button></div>}

        {stage === 'processing' || stage === 'uploading' ? <ProcessingView file={file} stage={stage} onCancel={() => setStage('idle')} /> : page === 'documents' ? <DocumentsView file={file} dragActive={dragActive} busy={busy} documents={documents} selectedId={selectedId} inputRef={fileInput} onFile={acceptFile} onDrag={setDragActive} onBrowse={() => fileInput.current?.click()} onRemove={() => setFile(null)} onUpload={uploadAndProcess} onSelect={selectDocument} onReprocess={reprocess} /> : <AnalysisView page={page} selected={selected} processingResults={processingResults} completeness={completeness} quality={quality} features={features} risk={risk} summary={summary} completenessScores={completenessScores} sections={sections} onNavigate={setPage} onReprocess={reprocess} busy={busy} />}
      </main>

      {chatOpen && <Assistant selected={selected} messages={messages} question={question} busy={chatBusy} onQuestion={setQuestion} onSubmit={submitQuestion} onClose={() => setChatOpen(false)} />}
    </div>
  )
}

function NavButton({ active, disabled, icon, label, onClick }: { active: boolean; disabled?: boolean; icon: ReactNode; label: string; onClick: () => void }) {
  return <button className={`nav-item ${active ? 'active' : ''}`} disabled={disabled} onClick={onClick}>{icon}<span>{label}</span>{active && <ArrowUpRight size={14} />}</button>
}

function DocumentsView(props: any) {
  return <section className="content-wrap"><div className="intro-row"><div><div className="section-kicker">START HERE</div><h2>Bring a DPR into focus.</h2><p>Upload a Detailed Project Report to extract structure, assess quality, and build a grounded question-answering workspace.</p></div><div className="intro-stat"><span>SUPPORTED</span><strong>PDF</strong><small>OCR + native text</small></div></div><div className="document-grid"><div className="upload-panel panel"><div className="panel-heading"><div><span className="section-kicker">NEW DOCUMENT</span><h3>Upload a report</h3></div><UploadCloud size={21} /></div><input ref={props.inputRef} hidden type="file" accept="application/pdf,.pdf" onChange={(event) => props.onFile(event.target.files?.[0])} /><div className={`dropzone ${props.dragActive ? 'drag-active' : ''} ${props.file ? 'has-file' : ''}`} onDragOver={(event) => { event.preventDefault(); props.onDrag(true) }} onDragLeave={() => props.onDrag(false)} onDrop={(event) => { event.preventDefault(); props.onDrag(false); props.onFile(event.dataTransfer.files?.[0]) }} onClick={!props.file ? props.onBrowse : undefined}>{props.file ? <><div className="file-badge"><FileText size={22} /></div><div className="file-name">{props.file.name}</div><div className="file-size">{(props.file.size / 1024 / 1024).toFixed(2)} MB</div><button className="remove-file" onClick={(event) => { event.stopPropagation(); props.onRemove() }}><X size={15} /> Remove</button></> : <><div className="upload-icon"><UploadCloud size={26} /></div><strong>Drop your PDF here</strong><span>or browse from your computer</span><button className="secondary-button" onClick={(event) => { event.stopPropagation(); props.onBrowse() }}>Browse files</button><small>PDF files up to your configured server limit</small></>}</div><button className="primary-button wide" disabled={!props.file || props.busy} onClick={props.onUpload}>{props.busy ? <LoaderCircle className="spin" size={17} /> : <Sparkles size={17} />} {props.busy ? 'Starting analysis...' : 'Upload & analyze'}</button></div><DocumentList documents={props.documents} selectedId={props.selectedId} onSelect={props.onSelect} onReprocess={props.onReprocess} /></div></section>
}

function DocumentList({ documents, selectedId, onSelect, onReprocess }: any) {
  return <div className="panel document-list-panel"><div className="panel-heading"><div><span className="section-kicker">DOCUMENT LIBRARY</span><h3>Recent reports <span className="count-badge">{documents.length}</span></h3></div><RefreshCw size={17} /></div>{documents.length === 0 ? <div className="empty-state"><FileText size={24} /><strong>No DPRs yet</strong><span>Your uploaded reports will appear here.</span></div> : <div className="document-list">{documents.map((document: DocumentRecord) => <button key={document.document_id} className={`document-row ${selectedId === document.document_id ? 'selected' : ''}`} onClick={() => onSelect(document)}><div className="doc-icon"><FileText size={17} /></div><div className="doc-copy"><strong>{document.filename}</strong><span>{document.document_id.slice(0, 8)}... · {String(document.metadata?.num_pages || '—')} pages</span></div><StatusBadge status={document.status} /><ChevronDown size={15} /></button>)}</div>}</div>
}

function StatusBadge({ status }: { status: string }) { return <span className={`status-badge ${status}`}>{status}</span> }

function ProcessingView({ file, stage, onCancel }: { file: File | null; stage: string; onCancel: () => void }) {
  return <section className="content-wrap processing-wrap"><div className="processing-header"><div><div className="section-kicker">LIVE WORKSPACE</div><h2>{stage === 'uploading' ? 'Uploading your report' : 'Pipeline running'}</h2><p>{stage === 'uploading' ? 'Securely sending the PDF to the DPR analysis service.' : 'The backend is running the complete analysis pipeline. This may take a few minutes.'}</p></div><div className="processing-orb"><LoaderCircle className="spin" size={30} /></div></div><div className="pipeline-card panel"><div className="pipeline-summary"><div><span className="section-kicker">CURRENT STATUS</span><strong>{stage === 'uploading' ? 'Uploading document...' : 'Running analysis pipeline...'}</strong></div><div className="pipeline-meta"><span>{file?.name}</span><span>Backend process active</span></div></div><div className="honest-progress"><div className="progress-track"><div className="progress-fill animated-fill" /></div><span>Pipeline running</span></div><div className="pipeline-list">{pipelineSteps.map(([title, description], index) => <div className="pipeline-step" key={title}><div className="step-icon"><LoaderCircle className="spin" size={16} /></div><div><strong>{String(index + 1).padStart(2, '0')} {title}</strong><span>{description}</span></div><em>Queued</em></div>)}</div><button className="text-button" onClick={onCancel}>Return to documents</button></div></section>
}

function AnalysisView(props: any) {
  const { page, selected, processingResults, completeness, quality, features, risk, summary, completenessScores, sections, onNavigate, onReprocess, busy } = props
  const riskAssessment = risk.risk_assessment || {}
  if (!selected) return <div className="content-wrap"><Empty title="No DPR selected" message="Upload or select a DPR to begin analysis." /></div>
  return <section className="content-wrap"><div className="analysis-header"><div><div className="section-kicker">ANALYSIS COMPLETE</div><h2>{selected.filename}</h2><p><span className="mono">{selected.document_id}</span> · {selected.metadata?.num_pages ? `${selected.metadata.num_pages} pages` : 'Processed document'}</p></div><button className="secondary-button" onClick={onReprocess} disabled={busy}><RefreshCw size={16} /> Reprocess</button></div>{page === 'analysis' ? <><div className="metric-grid"><Metric icon={<Layers3 size={18} />} label="Completeness" value={percentageText(completenessScores.completeness_score)} detail={completeness.completeness_level || 'Document structure'} accent="teal" onClick={() => onNavigate('completeness')} /><Metric icon={<Gauge size={18} />} label="Quality" value={percentageText(quality.document_quality_score)} detail={quality.document_quality_level || 'Document quality'} accent="orange" onClick={() => onNavigate('quality')} /><Metric icon={<Zap size={18} />} label="Document health" value={percentageText(features.overall_document_health)} detail="Combined document signal" accent="blue" onClick={() => onNavigate('features')} /><Metric icon={<ShieldCheck size={18} />} label="Risk score" value={percentageText(riskAssessment.risk_percentage, 2)} detail={`${riskAssessment.risk_level || 'Unavailable'} risk`} accent="red" onClick={() => onNavigate('risk')} /></div><div className="dashboard-grid"><RiskCard risk={riskAssessment} /><CompletenessChart data={summary} /><QualitySnapshot sections={sections} onNavigate={() => onNavigate('quality')} /></div></> : page === 'completeness' ? <CompletenessPanel data={completeness} scores={completenessScores} /> : page === 'quality' ? <QualityPanel sections={sections} quality={quality} /> : page === 'features' ? <FeaturePanel features={features} /> : <RiskPanel assessment={riskAssessment} />}</section>
}

function Metric({ icon, label, value, detail, accent, onClick }: any) { return <button className={`metric-card ${accent}`} onClick={onClick}><div className="metric-top"><span>{icon}</span><ArrowUpRight size={15} /></div><small>{label}</small><strong>{value}</strong><em>{detail}</em></button> }
function RiskCard({ risk }: any) { const percentage = toPercentage(risk.risk_percentage) ?? 0; return <div className="panel risk-card"><div className="panel-heading"><div><span className="section-kicker">RISK PROFILE</span><h3>Document risk</h3></div><ShieldCheck size={19} /></div><div className="risk-content"><div className="gauge" style={{ '--risk': `${percentage * 3.6}deg` } as CSSProperties}><div><strong>{percentageText(risk.risk_percentage, 2)}</strong><span>{risk.risk_level || 'UNAVAILABLE'} RISK</span></div></div><div className="risk-legend"><div><span className="legend-dot low" />Low exposure</div><div><span className="legend-dot medium" />Medium exposure</div><div><span className="legend-dot high" />High exposure</div></div></div></div> }
function CompletenessChart({ data }: any) { const found = safeNumber(data.found_sections); const missing = safeNumber(data.missing_sections); const total = (found ?? 0) + (missing ?? 0); const foundWidth = total ? (found ?? 0) / total * 100 : 0; const missingWidth = total ? (missing ?? 0) / total * 100 : 0; return <div className="panel chart-card"><div className="panel-heading"><div><span className="section-kicker">STRUCTURE SIGNAL</span><h3>Section coverage</h3></div><CircleHelp size={17} /></div><div className="coverage-number"><strong>{found === null ? '—' : found}</strong><span>found sections</span><b>{missing === null ? '—' : missing} missing</b></div><div className="stacked-bar"><div style={{ width: `${foundWidth}%` }} /><i style={{ width: `${missingWidth}%` }} /></div><div className="chart-key"><span><i className="key-found" />Found</span><span><i className="key-missing" />Missing</span></div></div> }
function QualitySnapshot({ sections, onNavigate }: any) { return <div className="panel chart-card"><div className="panel-heading"><div><span className="section-kicker">QUALITY SNAPSHOT</span><h3>Section performance</h3></div><button className="text-button" onClick={onNavigate}>View all</button></div>{sections.slice(0, 4).map((section: any) => <div className="mini-quality" key={section.section_id}><div><strong>{section.section_id}</strong><span>{section.title}</span></div><b>{percentageText(section.quality_score, 0)}</b><div className="mini-bar"><i style={{ width: `${scorePercent(section.quality_score)}%` }} /></div></div>)}</div> }
function CompletenessPanel({ data, scores }: any) { const missing = data.missing_sections || []; const found = data.found_sections || []; return <div className="analysis-panel-grid"><div className="panel detail-panel"><PanelTitle kicker="COMPLETENESS SIGNAL" title="Document structure" /><div className="score-strip"><BigScore value={percentageText(scores.completeness_score)} label={data.completeness_level || 'Overall'} /><BigScore value={percentageText(scores.critical_completeness_score)} label="Critical" /><BigScore value={percentageText(scores.weighted_completeness_score)} label="Weighted" /></div><div className="data-list"><DataLine label="Expected sections" value={data.summary?.total_expected_sections} /><DataLine label="Found sections" value={data.summary?.found_sections} /><DataLine label="Missing sections" value={data.summary?.missing_sections} /><DataLine label="Critical missing" value={data.summary?.critical_sections_missing} /></div></div><div className="panel detail-panel"><PanelTitle kicker="MISSING SECTIONS" title="Coverage gaps" /><div className="missing-list">{missing.length ? missing.map((item: any, index: number) => <div className="missing-row" key={item.id || item.name || index}><AlertCircle size={16} /><span>{typeof item === 'string' ? item : item.name}</span>{item.critical && <b>CRITICAL</b>}</div>) : <Empty title="No missing sections" message="The report covers every expected section." />}</div><div className="found-count"><Check size={15} /> {found.length} expected areas found</div></div></div> }
function QualityPanel({ sections, quality }: any) { const [sort, setSort] = useState('score'); const sorted = [...sections].sort((a: any, b: any) => sort === 'id' ? a.section_id.localeCompare(b.section_id) : (safeNumber(b.quality_score) ?? -1) - (safeNumber(a.quality_score) ?? -1)); return <div className="panel detail-panel quality-full"><div className="panel-heading"><PanelTitle kicker="SECTION QUALITY ANALYSIS" title="Quality by section" /><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="score">Sort by score</option><option value="id">Sort by section ID</option></select></div><div className="quality-summary"><BigScore value={percentageText(quality.document_quality_score)} label={quality.document_quality_level || 'Overall quality'} /><BigScore value={percentageText(quality.average_section_quality)} label="Average section" /><BigScore value={quality.sections.length} label="Sections rated" /></div><div className="quality-table">{sorted.map((section: any) => <div className="quality-row" key={section.section_id}><strong>{section.section_id}</strong><span>{section.title}</span><div className="quality-progress"><i style={{ width: `${scorePercent(section.quality_score)}%` }} /></div><b>{percentageText(section.quality_score, 0)}</b><em>{section.quality_level || 'RATED'}</em></div>)}</div></div> }
function FeaturePanel({ features }: any) { const groups: Array<[string, string[]]> = [['COMPLETENESS FEATURES', ['completeness_score', 'critical_completeness', 'weighted_completeness', 'found_section_ratio', 'missing_section_ratio']], ['QUALITY FEATURES', ['document_quality_score', 'average_section_quality', 'weak_section_ratio', 'excellent_section_ratio']], ['DOCUMENT HEALTH', ['overall_document_health', 'completeness_quality_gap', 'document_weakness_score']], ['SECTION STATISTICS', ['min_section_quality', 'max_section_quality', 'section_quality_range', 'section_quality_std_proxy']]]; return <div className="feature-groups">{groups.map(([title, keys]) => <div className="panel feature-group" key={title}><PanelTitle kicker={title} title={title === 'DOCUMENT HEALTH' ? 'Health indicators' : 'Signal profile'} />{keys.map((key) => <div className="feature-row" key={key}><span>{formatLabel(key)}</span><strong>{safeNumber(features[key]) === null ? '—' : safeNumber(features[key])!.toFixed(4)}</strong><div className="feature-track"><i style={{ width: `${Math.min(scorePercent(features[key]), 100)}%` }} /></div></div>)}</div>)}</div> }
function RiskPanel({ assessment }: any) { const components = assessment.component_risks || {}; return <div className="risk-layout"><div className="panel detail-panel"><PanelTitle kicker="RISK ASSESSMENT" title="Risk components" /><div className="risk-score-large"><strong>{percentageText(assessment.risk_percentage, 2)}</strong><span>{assessment.risk_level || 'UNAVAILABLE'} RISK</span></div>{Object.entries(components).map(([key, value]) => <div className="component-row" key={key}><span>{formatLabel(key)}</span><b>{percentageText(value, 1)}</b><div className="quality-progress"><i style={{ width: `${scorePercent(value)}%` }} /></div></div>)}</div><div className="panel detail-panel"><PanelTitle kicker="DRIVERS" title="Risk factors" /><FactorList title="Risk factors" items={assessment.risk_factors || []} negative /><FactorList title="Positive factors" items={assessment.positive_factors || []} /></div></div> }
function FactorList({ title, items, negative }: { title: string; items: any[]; negative?: boolean }) { return <div className="factor-block"><h4>{title}</h4>{items.length ? items.map((item, index) => <div className={`factor ${negative ? 'negative' : 'positive'}`} key={index}><span>{negative ? item.severity || 'SIGNAL' : 'GOOD'}</span><p>{typeof item === 'string' ? item : item.factor}</p></div>) : <span className="muted">No factors reported.</span>}</div> }
function PanelTitle({ kicker, title }: { kicker: string; title: string }) { return <div><span className="section-kicker">{kicker}</span><h3>{title}</h3></div> }
function BigScore({ value, label }: { value: string | number; label: string }) { return <div className="big-score"><strong>{value}</strong><span>{label}</span></div> }
function DataLine({ label, value }: { label: string; value: unknown }) { const number = safeNumber(value); return <div className="data-line"><span>{label}</span><strong>{number === null ? '—' : number}</strong></div> }
function Empty({ title, message }: { title: string; message: string }) { return <div className="empty-state"><CircleHelp size={23} /><strong>{title}</strong><span>{message}</span></div> }

function Assistant({ selected, messages, question, busy, onQuestion, onSubmit, onClose }: { selected: DocumentRecord | null | undefined; messages: ChatMessage[]; question: string; busy: boolean; onQuestion: (value: string) => void; onSubmit: (text?: string) => void; onClose: () => void }) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  return <aside className="assistant"><div className="assistant-head"><div className="assistant-title"><div className="bot-mark"><Bot size={18} /></div><div><strong>DPR AI Assistant</strong><span>{selected ? 'Ask questions about this DPR' : 'Select a processed DPR first'}</span></div></div><button className="icon-button subtle" title="Close assistant" onClick={onClose}><X size={17} /></button></div><div className="chat-body">{messages.length === 0 ? <div className="chat-empty"><div className="chat-orbit"><MessageSquare size={23} /></div><strong>Explore your report</strong><p>Ask a grounded question and inspect the source sections behind the answer.</p><div className="suggestions">{suggestions.map((suggestion) => <button key={suggestion} disabled={!selected || selected.status !== 'processed'} onClick={() => onSubmit(suggestion)}>{suggestion}<ArrowUpRight size={14} /></button>)}</div></div> : messages.map((message, index) => <div className={`message ${message.role}`} key={`${message.role}-${index}`}><div className="message-label">{message.role === 'user' ? 'You' : 'DPR AI'}</div><div className="message-bubble">{message.content}</div>{message.sources?.length ? <SourceList sources={message.sources} /> : null}</div>)}{busy && <div className="message assistant"><div className="message-label">DPR AI</div><div className="message-bubble loading-dots"><span /><span /><span /></div></div>}<div ref={messagesEndRef} aria-hidden="true" /></div><form className="chat-input" onSubmit={(event) => { event.preventDefault(); onSubmit() }}><Paperclip size={16} /><input value={question} onChange={(event) => onQuestion(event.target.value)} placeholder={selected ? 'Ask about this report...' : 'Select a processed DPR'} disabled={!selected || selected.status !== 'processed' || busy} /><button title="Send question" disabled={!question.trim() || busy}><Send size={16} /></button></form></aside>
}
function SourceList({ sources }: { sources: Source[] }) { return <details className="sources"><summary>Sources <span>{sources.length}</span></summary>{sources.map((source) => <div className="source-row" key={source.chunk_id}><strong>{source.section_id}</strong><span>{source.section_title}</span><b>{(source.similarity * 100).toFixed(1)}%</b></div>)}</details> }

export default App
