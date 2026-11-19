export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Status = 'passed' | 'failed' | 'healed' | 'error'

export interface Fingerprint {
  tag: string
  text: string
  label: string
  name: string
}
export interface Step {
  action: string
  value: string
  description: string
  target: { css: string; fingerprint: Fingerprint } | null
}
export interface TestCase {
  id: number
  title: string
  description: string
  category: string
  severity: Severity
  source: 'ai' | 'heuristic' | 'manual'
  page_url: string
  steps: Step[]
}
export interface Element {
  ref: string
  kind: string
  css: string
  fingerprint: Fingerprint
}
export interface SiteMap {
  base_url: string
  pages: { url: string; title: string; links: Element[]; buttons: Element[]; forms: { ref: string; kind: string; fields: Element[] }[] }[]
  broken_links: { url: string; status: number; found_on: string; text: string }[]
}
export interface RootCause {
  id: string
  title: string
  severity: Severity
  confidence: number
  affected_tests: string[]
  occurrences: number
  evidence: string[]
  suggested_fix: string
  method: string
}
export interface BugGroup {
  title: string
  error: string
  occurrences: number
  result_indices: number[]
  screenshots: string[]
}
export interface Summary {
  total: number
  passed: number
  failed: number
  healed: number
  error: number
  pass_rate: number
  healed_locators: number
  duration_ms: number
  root_causes?: RootCause[]
  unique_bugs?: number
  bugs?: BugGroup[]
}
export interface HealEvent {
  step_index: number
  old_css: string
  new_css: string
  score: number
  element: string
}
export interface TestResult {
  test_id: number
  title: string
  status: Status
  duration_ms: number
  error: string
  failed_step: number | null
  screenshot: string
  healed: HealEvent[]
  console_errors: string[]
}
export interface Run {
  id: number
  project_id: number
  status: string
  summary: Summary | null
  started_at: string
  finished_at: string | null
  results?: TestResult[]
}
export interface Project {
  id: number
  name: string
  base_url: string
  credentials: { username: string; password: string } | null
  site_map: SiteMap | null
  created_at: string
  test_count?: number
  last_summary?: Summary | null
}
export interface Health {
  status: string
  version: string
  ai_engine: string
  demo_url: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

export const api = {
  health: () => request<Health>('/api/health'),
  projects: () => request<Project[]>('/api/projects'),
  project: (id: number) => request<Project>(`/api/projects/${id}`),
  createProject: (body: { name: string; base_url: string; credentials?: { username: string; password: string } | null }) =>
    request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(body) }),
  deleteProject: (id: number) => request<void>(`/api/projects/${id}`, { method: 'DELETE' }),
  crawl: (id: number) => request<SiteMap>(`/api/projects/${id}/crawl`, { method: 'POST', body: '{}' }),
  generate: (id: number) =>
    request<{ engine: string; count: number; ai_count: number; tests: TestCase[] }>(`/api/projects/${id}/generate`, { method: 'POST' }),
  tests: (id: number) => request<TestCase[]>(`/api/projects/${id}/tests`),
  deleteTest: (pid: number, tid: number) => request<void>(`/api/projects/${pid}/tests/${tid}`, { method: 'DELETE' }),
  startRun: (id: number, body: { headless?: boolean; slow_mo?: number; self_heal?: boolean; test_ids?: number[] }) =>
    request<{ run_id: number; total: number }>(`/api/projects/${id}/runs`, { method: 'POST', body: JSON.stringify(body) }),
  runs: (id: number) => request<Run[]>(`/api/projects/${id}/runs`),
  run: (id: number) => request<Run>(`/api/runs/${id}`),
  demoVersion: () => request<{ version: number }>('/api/demo/version'),
  setDemoVersion: (version: number) => request<{ version: number }>('/api/demo/version', { method: 'PUT', body: JSON.stringify({ version }) }),
}

export const screenshotUrl = (runId: number, name: string) => `/api/runs/${runId}/screenshots/${name}`
export const reportUrl = (runId: number) => `/api/runs/${runId}/report.pdf`
export const exportUrl = (projectId: number) => `/api/projects/${projectId}/export.py`

export const capsuleUrl = (runId: number, resultIndex: number) => `/api/runs/${runId}/capsules/${resultIndex}`
