export function safeNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const number = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(number) ? number : null
}

export function toPercentage(value: unknown): number | null {
  const number = safeNumber(value)
  if (number === null) return null
  return number >= 0 && number <= 1 ? number * 100 : number
}

export function percentageText(value: unknown, digits = 1): string {
  const percentage = toPercentage(value)
  return percentage === null ? '—' : `${percentage.toFixed(digits)}%`
}

export function arrayValue(value: unknown): any[] {
  return Array.isArray(value) ? value : []
}

export function normalizeCompleteness(data: Record<string, any>) {
  const summary = data.summary || {}
  const scores = data.scores || {}
  const present = arrayValue(summary.present_sections || data.found_sections)
  const missing = arrayValue(summary.missing_sections || data.missing_sections)
  const expected = safeNumber(summary.total_expected_sections) ?? (present.length + missing.length || null)
  return {
    ...data,
    summary: {
      ...summary,
      found_sections: safeNumber(summary.found_sections) ?? (present.length || null),
      missing_sections: safeNumber(summary.missing_sections) ?? (missing.length || null),
      total_expected_sections: expected,
      critical_sections_missing: safeNumber(summary.critical_sections_missing),
    },
    found_sections: present,
    missing_sections: missing,
    scores: {
      ...scores,
      completeness_score: scores.completeness_score ?? summary.overall_score,
      critical_completeness_score: scores.critical_completeness_score,
      weighted_completeness_score: scores.weighted_completeness_score,
    },
  }
}

export function normalizeQuality(data: Record<string, any>) {
  return {
    ...data,
    document_quality_score: data.document_quality_score ?? data.summary?.overall_quality,
    average_section_quality: data.average_section_quality,
    sections: arrayValue(data.sections),
  }
}

export function normalizeRisk(data: Record<string, any>) {
  return { ...data, risk_assessment: data.risk_assessment || {} }
}