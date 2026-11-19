import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, Eye, FileDown, Loader2, PlayCircle, Sparkles, Wrench, XCircle } from 'lucide-react'
import { capsuleUrl, reportUrl, type HealEvent, type Summary, type TestCase, type TestResult } from '../api'
import { StatusBadge } from './ui'

type LogEntry = { id: number; kind: 'step' | 'heal' | 'pass' | 'fail' | 'info'; text: string }

interface RunEvent {
  type: string
  total?: number
  index?: number
  title?: string
  description?: string
  image?: string
  url?: string
  result?: TestResult
  summary?: Summary | null
  error?: string
}

export default function LiveRunTab({
  runId,
  tests,
  onStart,
  onFinished,
}: {
  runId: number | null
  tests: TestCase[]
  onStart: (o: { headless?: boolean; slow_mo?: number; self_heal?: boolean }) => void
  onFinished: () => void
}) {
  const [showBrowser, setShowBrowser] = useState(false)
  const [slowMo, setSlowMo] = useState(0)
  const [selfHeal, setSelfHeal] = useState(true)
  const [total, setTotal] = useState(0)
  const [current, setCurrent] = useState('')
  const [frame, setFrame] = useState<{ image: string; url: string } | null>(null)
  const [results, setResults] = useState<TestResult[]>([])
  const [log, setLog] = useState<LogEntry[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [running, setRunning] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!runId) return
    setResults([])
    setLog([])
    setSummary(null)
    setFrame(null)
    setRunning(true)
    let n = 0
    const add = (kind: LogEntry['kind'], text: string) => setLog((l) => [...l.slice(-300), { id: n++, kind, text }])
    const source = new EventSource(`/api/runs/${runId}/events`)
    source.onmessage = (msg) => {
      const e: RunEvent = JSON.parse(msg.data)
      switch (e.type) {
        case 'run_started':
          setTotal(e.total ?? 0)
          add('info', `Run #${runId} started with ${e.total} tests`)
          break
        case 'test_started':
          setCurrent(e.title ?? '')
          add('info', `▶ ${e.title}`)
          break
        case 'step':
          add('step', e.description ?? '')
          break
        case 'healed': {
          const h = e as unknown as HealEvent
          add('heal', `Self-healed ${h.element}: ${h.old_css} → ${h.new_css} (${Math.round(h.score * 100)}% match)`)
          break
        }
        case 'frame':
          if (e.image) setFrame({ image: e.image, url: e.url ?? '' })
          break
        case 'test_finished':
          if (e.result) {
            const r = e.result
            setResults((rs) => [...rs, r])
            add(r.status === 'failed' || r.status === 'error' ? 'fail' : 'pass', `${r.status.toUpperCase()}: ${r.title}${r.error ? ` — ${r.error}` : ''}`)
          }
          break
        case 'run_finished':
          setSummary(e.summary ?? null)
          setRunning(false)
          setCurrent('')
          add('info', e.error ? `Run failed: ${e.error}` : 'Run finished')
          source.close()
          onFinished()
          break
      }
    }
    source.onerror = () => {
      source.close()
      setRunning(false)
    }
    return () => source.close()
  }, [runId, onFinished])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight })
  }, [log])

  const done = results.length
  const pct = total ? Math.round((done / total) * 100) : 0
  const passed = results.filter((r) => r.status === 'passed' || r.status === 'healed').length
  const failed = done - passed
  const healed = results.reduce((n, r) => n + r.healed.length, 0)

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-center gap-6 text-sm">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={selfHeal} onChange={(e) => setSelfHeal(e.target.checked)} /> Self-healing locators
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={showBrowser} onChange={(e) => setShowBrowser(e.target.checked)} /> Open real browser window on this machine
        </label>
        <label className="flex items-center gap-2">
          Speed
          <select className="input w-36 py-1" value={slowMo} onChange={(e) => setSlowMo(Number(e.target.value))}>
            <option value={0}>Fast</option>
            <option value={250}>Presentation</option>
            <option value={700}>Slow motion</option>
          </select>
        </label>
        <button
          className="btn-primary ml-auto"
          disabled={running || tests.length === 0}
          onClick={() => onStart({ headless: !showBrowser, slow_mo: slowMo, self_heal: selfHeal })}
        >
          {running ? <Loader2 size={16} className="animate-spin" /> : <PlayCircle size={16} />} {running ? 'Running…' : `Run ${tests.length} tests`}
        </button>
      </div>

      {!runId ? (
        <div className="card py-16 text-center text-slate-400">Start a run to watch the AI test your website live.</div>
      ) : (
        <>
          <div className="card">
            <div className="flex items-center justify-between text-sm">
              <span className="truncate text-slate-300">{running ? `Running: ${current}` : summary ? 'Completed' : 'Waiting…'}</span>
              <span className="text-slate-400">
                {done}/{total} · <span className="text-emerald-400">{passed} passed</span> ·{' '}
                <span className="text-rose-400">{failed} failed</span> · <span className="text-sky-300">{healed} healed</span>
              </span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full bg-gradient-to-r from-indigo-500 to-fuchsia-500 transition-all" style={{ width: `${pct}%` }} />
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-5">
            <div className="card lg:col-span-3">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <Eye size={16} /> Live browser view
                {running && <span className="ml-1 h-2 w-2 animate-pulse rounded-full bg-rose-500" />}
                <span className="ml-auto truncate font-mono text-xs font-normal text-slate-500">{frame?.url}</span>
              </div>
              <div className="aspect-[16/10] overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
                {frame ? (
                  <img src={`data:image/jpeg;base64,${frame.image}`} alt="Live browser" className="h-full w-full object-contain" />
                ) : (
                  <div className="grid h-full place-items-center text-sm text-slate-500">Launching browser…</div>
                )}
              </div>
            </div>
            <div className="card flex flex-col lg:col-span-2">
              <div className="mb-2 text-sm font-semibold">Execution log</div>
              <div ref={logRef} className="h-[22rem] flex-1 space-y-1 overflow-y-auto font-mono text-xs">
                {log.map((l) => (
                  <div
                    key={l.id}
                    className={
                      {
                        step: 'pl-4 text-slate-400',
                        heal: 'rounded bg-sky-500/10 px-2 py-1 text-sky-300',
                        pass: 'text-emerald-400',
                        fail: 'rounded bg-rose-500/10 px-2 py-1 text-rose-300',
                        info: 'pt-1 font-semibold text-slate-200',
                      }[l.kind]
                    }
                  >
                    {l.kind === 'heal' && <Wrench size={12} className="mr-1 inline" />}
                    {l.text}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {summary && (
            <div className="card flex flex-wrap items-center gap-6">
              <Sparkles className="text-fuchsia-300" />
              <div>
                <div className="text-2xl font-bold">{summary.pass_rate}% pass rate</div>
                <div className="text-sm text-slate-400">
                  {summary.unique_bugs ?? (summary.failed + summary.error)} unique bugs ({summary.failed + summary.error} failing tests) · {summary.healed_locators} selectors self-healed · {(summary.duration_ms / 1000).toFixed(1)}s
                </div>
              </div>
              <a href={reportUrl(runId)} className="btn-primary ml-auto">
                <FileDown size={16} /> Download PDF report
              </a>
            </div>
          )}

          {summary && (
            <div className="card">
              <div className="mb-3 flex items-center gap-2 font-semibold">
                <Sparkles size={16} className="text-amber-300" /> Root cause analysis ({summary.root_causes?.length ?? 0})
              </div>
              {(summary.root_causes?.length ?? 0) === 0 ? (
                <p className="text-sm text-slate-400">No failure pattern could be confidently classified. Check the failure details and screenshots.</p>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {summary.root_causes?.map((cause) => (
                    <div key={cause.id} className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold">{cause.title}</span>
                        <span className="rounded bg-amber-500/15 px-2 py-1 text-xs text-amber-200">{Math.round(cause.confidence * 100)}% confidence</span>
                      </div>
                      <div className="mt-1 text-xs text-slate-400">{cause.severity.toUpperCase()} · {cause.occurrences} related failure(s)</div>
                      <div className="mt-2 text-xs text-slate-300">Affected tests: {cause.affected_tests.join(', ')}</div>
                      {cause.evidence.map((item, i) => <div key={i} className="mt-2 break-words font-mono text-xs text-rose-300">Evidence: {item}</div>)}
                      <div className="mt-2 text-sm text-emerald-200">Suggested fix: {cause.suggested_fix}</div>
                      <div className="mt-2 text-[11px] text-slate-500">{cause.method}; likely cause, not a confirmed diagnosis.</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {results.length > 0 && (
            <div className="overflow-hidden rounded-2xl border border-slate-800">
              {results.map((r, i) => (
                <div key={i} className="flex items-center gap-3 border-b border-slate-800 bg-slate-900/40 px-4 py-2 text-sm last:border-0">
                  {r.status === 'failed' || r.status === 'error' ? (
                    <XCircle size={16} className="text-rose-400" />
                  ) : (
                    <CheckCircle2 size={16} className={r.status === 'healed' ? 'text-sky-300' : 'text-emerald-400'} />
                  )}
                  <span className="flex-1 truncate">{r.title}</span>
                  {r.error && <span className="max-w-md truncate text-xs text-rose-300">{r.error}</span>}
                  <StatusBadge status={r.status} />
                  {(r.status === 'failed' || r.status === 'error') && (
                    <a
                      className="rounded-md border border-amber-500/30 px-2 py-1 text-xs text-amber-200 hover:bg-amber-500/10"
                      href={capsuleUrl(runId, i)}
                      title="Download a portable reproduction capsule with test steps and evidence"
                    >
                      Bug Replay Capsule
                    </a>
                  )}
                  <span className="w-12 text-right text-xs text-slate-500">{(r.duration_ms / 1000).toFixed(1)}s</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
