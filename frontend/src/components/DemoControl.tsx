import { useEffect, useState } from 'react'
import { Shuffle } from 'lucide-react'
import { api } from '../api'

export default function DemoControl() {
  const [version, setVersion] = useState<number | null>(null)

  useEffect(() => {
    api.demoVersion().then((v) => setVersion(v.version)).catch(() => setVersion(null))
  }, [])

  const toggle = async () => {
    const next = version === 1 ? 2 : 1
    const res = await api.setDemoVersion(next)
    setVersion(res.version)
  }

  if (version === null) return null
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-fuchsia-500/30 bg-fuchsia-500/5 px-4 py-3 text-sm">
      <Shuffle size={16} className="text-fuchsia-300" />
      <span>
        Demo store is on <b>v{version}</b>
        {version === 2 ? ' (redesigned UI: IDs, classes and button texts changed)' : ' (original UI)'}.
      </span>
      <button onClick={toggle} className="btn-ghost ml-auto py-1">
        {version === 1 ? 'Deploy v2 redesign (breaks selectors)' : 'Roll back to v1'}
      </button>
    </div>
  )
}
