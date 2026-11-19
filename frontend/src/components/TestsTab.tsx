import { useMemo, useState } from 'react'
import { Bot, ChevronDown, ChevronRight, Download, Play, Trash2, Workflow } from 'lucide-react'
import { api, exportUrl, type TestCase } from '../api'
import { Badge, Empty, SeverityBadge } from './ui'

export default function TestsTab({
  projectId,
  tests,
  onRunOne,
  onDeleted,
}: {
  projectId: number
  tests: TestCase[]
  onRunOne: (id: number) => void
  onDeleted: () => void
}) {
  const [open, setOpen] = useState<number | null>(null)
  const [filter, setFilter] = useState('all')
  const categories = useMemo(() => ['all', ...new Set(tests.map((t) => t.category))], [tests])
  const shown = filter === 'all' ? tests : tests.filter((t) => t.category === filter)

  if (tests.length === 0) return <Empty title="No test cases yet">Crawl the site, then click “2. Generate tests”.</Empty>

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {categories.map((c) => (
          <button
            key={c}
            onClick={() => setFilter(c)}
            className={`rounded-full px-3 py-1 text-xs capitalize ${filter === c ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
          >
            {c}
          </button>
        ))}
        <a href={exportUrl(projectId)} className="btn-ghost ml-auto py-1.5">
          <Download size={14} /> Export as Playwright (pytest)
        </a>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-800">
        {shown.map((t) => (
          <div key={t.id} className="border-b border-slate-800 bg-slate-900/40 last:border-0">
            <div className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-slate-800/40" onClick={() => setOpen(open === t.id ? null : t.id)}>
              {open === t.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{t.title}</div>
                <div className="truncate text-xs text-slate-500">{t.description}</div>
              </div>
              <Badge className="bg-slate-700/40 capitalize text-slate-300 ring-slate-600">{t.category}</Badge>
              <SeverityBadge severity={t.severity} />
              {t.source === 'ai' ? (
                <Badge className="bg-fuchsia-500/15 text-fuchsia-300 ring-fuchsia-500/30">
                  <Bot size={12} /> LLM
                </Badge>
              ) : (
                <Badge className="bg-indigo-500/15 text-indigo-300 ring-indigo-500/30">
                  <Workflow size={12} /> Rule engine
                </Badge>
              )}
              <button
                className="text-slate-400 hover:text-emerald-400"
                title="Run this test"
                onClick={(e) => {
                  e.stopPropagation()
                  onRunOne(t.id)
                }}
              >
                <Play size={16} />
              </button>
              <button
                className="text-slate-500 hover:text-rose-400"
                title="Delete test"
                onClick={async (e) => {
                  e.stopPropagation()
                  await api.deleteTest(projectId, t.id)
                  onDeleted()
                }}
              >
                <Trash2 size={16} />
              </button>
            </div>
            {open === t.id && (
              <ol className="space-y-1 bg-slate-950/60 px-12 py-3 text-sm">
                {t.steps.map((s, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="w-5 text-right text-slate-500">{i + 1}.</span>
                    <span className="w-44 shrink-0 font-mono text-xs leading-5 text-indigo-300">{s.action}</span>
                    <span className="text-slate-300">{s.description}</span>
                    {s.target && <code className="ml-auto truncate text-xs text-slate-500">{s.target.css}</code>}
                  </li>
                ))}
              </ol>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
