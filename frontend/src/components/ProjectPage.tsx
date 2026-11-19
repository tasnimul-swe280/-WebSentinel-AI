import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Bot, Globe, History, LayoutDashboard, ListChecks, PlayCircle, Radar, Wand2 } from 'lucide-react'
import { api, type Health, type Project, type Run, type TestCase } from '../api'
import OverviewTab from './OverviewTab'
import TestsTab from './TestsTab'
import LiveRunTab from './LiveRunTab'
import HistoryTab from './HistoryTab'
import DemoControl from './DemoControl'
import { ErrorBox, Spinner } from './ui'

type Tab = 'overview' | 'tests' | 'live' | 'history'

export default function ProjectPage({ projectId, health, onBack }: { projectId: number; health: Health | null; onBack: () => void }) {
  const [project, setProject] = useState<Project | null>(null)
  const [tests, setTests] = useState<TestCase[]>([])
  const [runs, setRuns] = useState<Run[]>([])
  const [tab, setTab] = useState<Tab>('overview')
  const [busy, setBusy] = useState<'' | 'crawl' | 'generate'>('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [activeRun, setActiveRun] = useState<number | null>(null)

  const reload = useCallback(async () => {
    try {
      const [p, t, r] = await Promise.all([api.project(projectId), api.tests(projectId), api.runs(projectId)])
      setProject(p)
      setTests(t)
      setRuns(r)
    } catch (e) {
      setError((e as Error).message)
    }
  }, [projectId])

  useEffect(() => {
    reload()
  }, [reload])

  const action = async (kind: 'crawl' | 'generate') => {
    setBusy(kind)
    setError('')
    setNotice('')
    try {
      if (kind === 'crawl') {
        const site = await api.crawl(projectId)
        setNotice(`Discovered ${site.pages.length} pages, ${site.pages.reduce((n, p) => n + p.forms.length, 0)} forms and ${site.broken_links.length} broken links.`)
        setTab('overview')
      } else {
        const res = await api.generate(projectId)
        setNotice(`Generated ${res.count} test cases (${res.ai_count} written by ${res.engine}).`)
        setTab('tests')
      }
      await reload()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy('')
    }
  }

  const startRun = async (options: { headless?: boolean; slow_mo?: number; self_heal?: boolean; test_ids?: number[] } = {}) => {
    setError('')
    try {
      const { run_id } = await api.startRun(projectId, options)
      setActiveRun(run_id)
      setTab('live')
    } catch (e) {
      setError((e as Error).message)
    }
  }

  if (!project) return <div className="flex items-center gap-2 text-slate-400"><Spinner /> Loading…</div>

  const crawled = !!project.site_map
  const isDemo = project.base_url.includes('/demo')
  const tabs: { id: Tab; label: string; icon: typeof ListChecks; count?: number }[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'tests', label: 'Test cases', icon: ListChecks, count: tests.length },
    { id: 'live', label: 'Live run', icon: PlayCircle },
    { id: 'history', label: 'Reports', icon: History, count: runs.length },
  ]

  return (
    <div className="space-y-6">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-400 hover:text-white">
        <ArrowLeft size={14} /> All projects
      </button>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">{project.name}</h1>
          <a href={project.base_url} target="_blank" rel="noreferrer" className="mt-1 flex items-center gap-1 text-sm text-indigo-300 hover:underline">
            <Globe size={14} /> {project.base_url}
          </a>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-ghost" onClick={() => action('crawl')} disabled={!!busy}>
            {busy === 'crawl' ? <Spinner /> : <Radar size={16} />} 1. Crawl site
          </button>
          <button className="btn-ghost" onClick={() => action('generate')} disabled={!!busy || !crawled}>
            {busy === 'generate' ? <Spinner /> : <Wand2 size={16} />} 2. Generate tests
          </button>
          <button className="btn-primary" onClick={() => startRun()} disabled={!!busy || tests.length === 0}>
            <PlayCircle size={16} /> 3. Run all tests
          </button>
        </div>
      </div>

      {busy === 'generate' && (
        <div className="flex items-center gap-2 rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-4 py-2 text-sm text-indigo-200">
          <Bot size={16} /> {health?.ai_engine ?? 'AI'} is analysing pages and writing test cases…
        </div>
      )}
      {notice && <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-200">{notice}</div>}
      <ErrorBox message={error} />
      {isDemo && <DemoControl />}

      <nav className="flex gap-1 border-b border-slate-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition ${
              tab === t.id ? 'border-indigo-500 text-white' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <t.icon size={16} /> {t.label}
            {t.count !== undefined && <span className="rounded-full bg-slate-800 px-2 text-xs">{t.count}</span>}
          </button>
        ))}
      </nav>

      {tab === 'overview' && <OverviewTab project={project} tests={tests} runs={runs} />}
      {tab === 'tests' && (
        <TestsTab
          projectId={projectId}
          tests={tests}
          onRunOne={(id) => startRun({ test_ids: [id] })}
          onDeleted={reload}
        />
      )}
      {tab === 'live' && <LiveRunTab runId={activeRun} tests={tests} onStart={startRun} onFinished={reload} />}
      {tab === 'history' && <HistoryTab runs={runs} tests={tests} />}
    </div>
  )
}
