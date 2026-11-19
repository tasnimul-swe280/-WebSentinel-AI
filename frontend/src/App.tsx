import { useEffect, useState } from 'react'
import { Bot, FlaskConical } from 'lucide-react'
import { api, type Health } from './api'
import ProjectsPage from './components/ProjectsPage'
import ProjectPage from './components/ProjectPage'

function readProjectId(): number | null {
  const match = window.location.hash.match(/^#\/projects\/(\d+)/)
  return match ? Number(match[1]) : null
}

export default function App() {
  const [projectId, setProjectId] = useState<number | null>(readProjectId)
  const [health, setHealth] = useState<Health | null>(null)

  useEffect(() => {
    const onHash = () => setProjectId(readProjectId())
    window.addEventListener('hashchange', onHash)
    api.health().then(setHealth).catch(() => setHealth(null))
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const open = (id: number | null) => {
    window.location.hash = id ? `#/projects/${id}` : '#/'
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_rgba(79,70,229,0.18),_transparent_60%)]">
      <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-6 py-4">
          <button onClick={() => open(null)} className="flex items-center gap-2 text-lg font-bold">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-fuchsia-500">
              <FlaskConical size={20} />
            </span>
            WebSentinel<span className="text-indigo-400">-AI</span>
          </button>
          <span className="hidden text-sm text-slate-400 md:inline">AI-powered automated web testing with self-healing locators</span>
          <div className="ml-auto flex items-center gap-2 text-xs">
            <span className={`h-2 w-2 rounded-full ${health ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            <Bot size={14} className="text-slate-400" />
            <span className="text-slate-300">{health ? `AI engine: ${health.ai_engine}` : 'Backend offline'}</span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">
        {projectId ? (
          <ProjectPage projectId={projectId} health={health} onBack={() => open(null)} />
        ) : (
          <ProjectsPage health={health} onOpen={open} />
        )}
      </main>
    </div>
  )
}
