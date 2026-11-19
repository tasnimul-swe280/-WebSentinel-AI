import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { FileText, Link2Off, SquareStack } from 'lucide-react'
import type { Project, Run, Status, TestCase } from '../api'
import { Empty, STATUS_COLORS, Stat } from './ui'

const tooltipStyle = { background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }

export default function OverviewTab({ project, tests, runs }: { project: Project; tests: TestCase[]; runs: Run[] }) {
  const site = project.site_map
  if (!site) return <Empty title="Start by crawling the website">Click “1. Crawl site” and WebSentinel-AI will explore every page with a real browser.</Empty>

  const forms = site.pages.reduce((n, p) => n + p.forms.length, 0)
  const lastRun = runs.find((r) => r.status === 'finished' && r.summary)
  const s = lastRun?.summary
  const statusData = s
    ? (['passed', 'healed', 'failed', 'error'] as Status[]).map((k) => ({ name: k, value: s[k] })).filter((d) => d.value > 0)
    : []
  const categories = Object.entries(
    tests.reduce<Record<string, number>>((acc, t) => ({ ...acc, [t.category]: (acc[t.category] ?? 0) + 1 }), {}),
  ).map(([name, count]) => ({ name, count }))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Pages discovered" value={site.pages.length} hint={`${forms} forms`} />
        <Stat label="Test cases" value={tests.length} hint={`${tests.filter((t) => t.source === 'ai').length} written by LLM`} />
        <Stat
          label="Last pass rate"
          value={s ? `${s.pass_rate}%` : '—'}
          accent={s ? (s.pass_rate >= 90 ? 'text-emerald-400' : 'text-amber-300') : 'text-white'}
          hint={s ? `${s.failed + s.error} bugs found` : 'No runs yet'}
        />
        <Stat label="Self-healed selectors" value={s?.healed_locators ?? 0} accent="text-sky-300" hint="Broken selectors fixed automatically" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="mb-2 font-semibold">Last run result</div>
          {statusData.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={3}>
                  {statusData.map((d) => (
                    <Cell key={d.name} fill={STATUS_COLORS[d.name as Status]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="py-16 text-center text-sm text-slate-500">Run the tests to see results.</div>
          )}
          <div className="flex justify-center gap-4 text-xs">
            {statusData.map((d) => (
              <span key={d.name} className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full" style={{ background: STATUS_COLORS[d.name as Status] }} /> {d.name}: {d.value}
              </span>
            ))}
          </div>
        </div>
        <div className="card">
          <div className="mb-2 font-semibold">Test coverage by category</div>
          {categories.length ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={categories}>
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                <YAxis allowDecimals={false} stroke="#94a3b8" fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(99,102,241,0.1)' }} />
                <Bar dataKey="count" fill="#6366f1" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="py-16 text-center text-sm text-slate-500">Generate tests to see coverage.</div>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <div className="mb-3 flex items-center gap-2 font-semibold">
            <SquareStack size={16} /> Site map
          </div>
          <div className="divide-y divide-slate-800">
            {site.pages.map((p) => (
              <div key={p.url} className="flex items-center justify-between gap-4 py-2 text-sm">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 font-medium">
                    <FileText size={14} className="text-slate-500" /> {p.title || 'Untitled'}
                  </div>
                  <div className="truncate text-xs text-slate-500">{p.url}</div>
                </div>
                <div className="flex shrink-0 gap-3 text-xs text-slate-400">
                  <span>{p.links.length} links</span>
                  {p.forms.map((f) => (
                    <span key={f.ref} className="rounded bg-indigo-500/15 px-2 text-indigo-200">
                      {f.kind} form
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <div className="mb-3 flex items-center gap-2 font-semibold">
            <Link2Off size={16} className="text-rose-400" /> Broken links ({site.broken_links.length})
          </div>
          {site.broken_links.length === 0 ? (
            <div className="text-sm text-slate-500">No broken links found.</div>
          ) : (
            site.broken_links.map((b) => (
              <div key={b.url} className="mb-2 rounded-lg bg-rose-500/10 p-2 text-xs">
                <div className="font-semibold text-rose-300">
                  HTTP {b.status} · {b.text || 'link'}
                </div>
                <div className="truncate text-slate-400">{b.url}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
