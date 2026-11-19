import { useEffect, useState, type FormEvent } from 'react'
import { Globe, Plus, Sparkles, Trash2 } from 'lucide-react'
import { api, type Health, type Project } from '../api'
import { Empty, ErrorBox, Spinner } from './ui'

export default function ProjectsPage({ health, onOpen }: { health: Health | null; onOpen: (id: number) => void }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = () => api.projects().then(setProjects).catch((e) => setError(e.message))
  useEffect(() => {
    load()
  }, [])

  const create = async (body: Parameters<typeof api.createProject>[0]) => {
    setBusy(true)
    setError('')
    try {
      const project = await api.createProject(body)
      onOpen(project.id)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    create({ name, base_url: url, credentials: username && password ? { username, password } : null })
  }

  const createDemo = () =>
    create({
      name: 'ShopLite Demo Store',
      base_url: health?.demo_url ?? `${window.location.origin}/demo/`,
      credentials: { username: 'demo', password: 'demo123' },
    })

  const remove = async (id: number) => {
    if (!confirm('Delete this project and all its test runs?')) return
    await api.deleteProject(id)
    load()
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <h1 className="text-4xl font-extrabold leading-tight">
            Paste a URL. <span className="bg-gradient-to-r from-indigo-400 to-fuchsia-400 bg-clip-text text-transparent">AI tests it for you.</span>
          </h1>
          <p className="mt-3 max-w-xl text-slate-400">
            WebSentinel-AI crawls your website with a real browser, writes end-to-end test cases, runs them live, heals broken selectors
            automatically and gives you a bug report — in minutes, without writing a single line of test code.
          </p>
          <div className="mt-6 grid max-w-xl grid-cols-2 gap-3 text-sm text-slate-300 sm:grid-cols-4">
            {['1. Crawl', '2. Generate', '3. Run & Heal', '4. Report'].map((s) => (
              <div key={s} className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-center">
                {s}
              </div>
            ))}
          </div>
          <button onClick={createDemo} disabled={busy} className="btn-primary mt-6">
            {busy ? <Spinner /> : <Sparkles size={16} />} Try the built-in demo store
          </button>
        </div>
        <form onSubmit={submit} className="card space-y-3 lg:col-span-2">
          <div className="flex items-center gap-2 font-semibold">
            <Plus size={18} /> New project
          </div>
          <input className="input" placeholder="Project name" value={name} onChange={(e) => setName(e.target.value)} required />
          <input className="input" placeholder="https://your-website.com" value={url} onChange={(e) => setUrl(e.target.value)} required pattern="https?://.+" />
          <div className="text-xs text-slate-500">Optional test login (used for login test cases)</div>
          <div className="grid grid-cols-2 gap-2">
            <input className="input" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
            <input className="input" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn-primary w-full justify-center" disabled={busy}>
            Create project
          </button>
        </form>
      </section>

      <ErrorBox message={error} />

      <section>
        <h2 className="mb-3 text-lg font-semibold">Projects</h2>
        {projects.length === 0 ? (
          <Empty title="No projects yet">Create one above, or start with the demo store.</Empty>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <div key={p.id} className="card group cursor-pointer transition hover:border-indigo-500/60" onClick={() => onOpen(p.id)}>
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold">{p.name}</div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      remove(p.id)
                    }}
                    className="text-slate-500 opacity-0 transition hover:text-rose-400 group-hover:opacity-100"
                    aria-label="Delete project"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="mt-1 flex items-center gap-1 truncate text-xs text-slate-400">
                  <Globe size={12} /> {p.base_url}
                </div>
                <div className="mt-4 flex gap-4 text-sm">
                  <span>
                    <b>{p.test_count ?? 0}</b> <span className="text-slate-400">tests</span>
                  </span>
                  {p.last_summary && (
                    <span>
                      <b className={p.last_summary.pass_rate >= 90 ? 'text-emerald-400' : 'text-amber-300'}>{p.last_summary.pass_rate}%</b>{' '}
                      <span className="text-slate-400">last pass rate</span>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
