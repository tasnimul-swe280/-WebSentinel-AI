import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Bug, FileDown, Wrench } from 'lucide-react'
import { api, reportUrl, screenshotUrl, type Run, type TestCase } from '../api'
import { Empty, SeverityBadge, StatusBadge } from './ui'

const SEVERITY_RANK = { critical: 0, high: 1, medium: 2, low: 3 }

export default function HistoryTab({ runs, tests }: { runs: Run[]; tests: TestCase[] }) {
  const finished = runs.filter((r) => r.summary && r.status === 'finished')
  const [selected, setSelected] = useState<number | null>(finished[0]?.id ?? null)
  const [run, setRun] = useState<Run | null>(null)

  useEffect(() => {
    if (selected) api.run(selected).then(setRun)
  }, [selected])

  if (finished.length === 0) return <Empty title="No reports yet">Run the tests to generate your first report.</Empty>

  const testById = new Map(tests.map((t) => [t.id, t]))
  const trend = [...finished].reverse().map((r) => ({ run: `#${r.id}`, pass_rate: r.summary!.pass_rate, bugs: r.summary!.failed + r.summary!.error }))
  const bugGroups = run?.summary?.bugs ?? (run?.results ?? [])
    .map((r, index) => ({ r, index }))
    .filter(({ r }) => r.status === 'failed' || r.status === 'error')
    .map(({ r, index }) => ({ title: r.title, error: r.error, occurrences: 1, result_indices: [index], screenshots: r.screenshot ? [r.screenshot] : [] }))
  const bugs = [...bugGroups].sort((a, b) => {
    const ai = (run?.results ?? [])[a.result_indices[0]]
    const bi = (run?.results ?? [])[b.result_indices[0]]
    return SEVERITY_RANK[testById.get(ai?.test_id)?.severity ?? 'low'] - SEVERITY_RANK[testById.get(bi?.test_id)?.severity ?? 'low']
  })
  const heals = (run?.results ?? []).flatMap((r) => r.healed.map((h) => ({ ...h, title: r.title })))

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <div className="mb-2 font-semibold">Quality trend</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trend}>
              <CartesianGrid stroke="#1e293b" />
              <XAxis dataKey="run" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }} />
              <Line type="monotone" dataKey="pass_rate" stroke="#10b981" strokeWidth={2} name="Pass rate %" />
              <Line type="monotone" dataKey="bugs" stroke="#f43f5e" strokeWidth={2} name="Bugs" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card max-h-[16rem] overflow-y-auto">
          <div className="mb-2 font-semibold">Runs</div>
          {finished.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelected(r.id)}
              className={`mb-1 flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm ${selected === r.id ? 'bg-indigo-600/30' : 'hover:bg-slate-800'}`}
            >
              <span>
                Run #{r.id} <span className="text-xs text-slate-500">{new Date(r.started_at).toLocaleString()}</span>
              </span>
              <span className={r.summary!.pass_rate >= 90 ? 'text-emerald-400' : 'text-amber-300'}>{r.summary!.pass_rate}%</span>
            </button>
          ))}
        </div>
      </div>

      {run && (
        <>
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Run #{run.id} report</h3>
            <a href={reportUrl(run.id)} className="btn-primary">
              <FileDown size={16} /> Download PDF
            </a>
          </div>

          <div className="card">
            <div className="mb-3 flex items-center gap-2 font-semibold">
              <Bug size={16} className="text-amber-300" /> Root cause analysis ({run.summary?.root_causes?.length ?? 0})
            </div>
            {(run.summary?.root_causes?.length ?? 0) === 0 ? (
              <p className="text-sm text-slate-400">No failure pattern could be confidently classified. Review the individual failure evidence below.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {run.summary!.root_causes!.map((cause) => (
                  <div key={cause.id} className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-slate-100">{cause.title}</span>
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

          <div className="card">
            <div className="mb-3 flex items-center gap-2 font-semibold">
              <Bug size={16} className="text-rose-400" /> Unique bugs found ({bugs.length}) · {(run?.summary?.failed ?? 0) + (run?.summary?.error ?? 0)} failing test results
            </div>
            {bugs.length === 0 && <div className="text-sm text-emerald-300">No bugs. Every test passed.</div>}
            <div className="grid gap-4 md:grid-cols-2">
              {bugs.map((b, i) => {
                const representative = (run?.results ?? [])[b.result_indices[0]]
                const t = representative ? testById.get(representative.test_id) : undefined
                const screenshot = b.screenshots[0]
                return (
                  <div key={i} className="overflow-hidden rounded-xl border border-rose-500/30 bg-slate-950">
                    {screenshot && (
                      <a href={screenshotUrl(run.id, screenshot)} target="_blank" rel="noreferrer">
                        <img src={screenshotUrl(run.id, screenshot)} alt="Failure screenshot" className="h-40 w-full object-cover object-top" />
                      </a>
                    )}
                    <div className="space-y-1 p-3 text-sm">
                      <div className="flex items-center gap-2">
                        {t && <SeverityBadge severity={t.severity} />}
                        <span className="font-semibold">{b.title}</span>
                        <span className="ml-auto rounded bg-rose-500/10 px-2 py-1 text-xs text-rose-200">{b.occurrences} occurrence(s)</span>
                      </div>
                      {t && <div className="text-xs text-slate-400">{t.description}</div>}
                      <div className="font-mono text-xs text-rose-300">{b.error}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {heals.length > 0 && (
            <div className="card">
              <div className="mb-3 flex items-center gap-2 font-semibold">
                <Wrench size={16} className="text-sky-300" /> Self-healed selectors ({heals.length})
              </div>
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-1">Test</th>
                    <th>Element</th>
                    <th>Broken selector</th>
                    <th>Healed selector</th>
                    <th>Match</th>
                  </tr>
                </thead>
                <tbody>
                  {heals.map((h, i) => (
                    <tr key={i} className="border-t border-slate-800">
                      <td className="py-1.5 pr-2">{h.title}</td>
                      <td className="text-slate-300">{h.element}</td>
                      <td className="font-mono text-xs text-rose-300 line-through">{h.old_css}</td>
                      <td className="font-mono text-xs text-emerald-300">{h.new_css}</td>
                      <td>{Math.round(h.score * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="overflow-hidden rounded-2xl border border-slate-800">
            {(run.results ?? []).map((r, i) => (
              <div key={i} className="flex items-center gap-3 border-b border-slate-800 bg-slate-900/40 px-4 py-2 text-sm last:border-0">
                <span className="w-6 text-slate-500">{i + 1}</span>
                <span className="flex-1 truncate">{r.title}</span>
                <StatusBadge status={r.status} />
                <span className="w-12 text-right text-xs text-slate-500">{(r.duration_ms / 1000).toFixed(1)}s</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
