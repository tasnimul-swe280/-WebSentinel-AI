import type { ReactNode } from 'react'
import type { Severity, Status } from '../api'

const severityStyle: Record<Severity, string> = {
  critical: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  high: 'bg-orange-500/15 text-orange-300 ring-orange-500/30',
  medium: 'bg-amber-500/15 text-amber-200 ring-amber-500/30',
  low: 'bg-slate-500/15 text-slate-300 ring-slate-500/30',
}

const statusStyle: Record<Status, string> = {
  passed: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  healed: 'bg-sky-500/15 text-sky-300 ring-sky-500/30',
  failed: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  error: 'bg-orange-500/15 text-orange-300 ring-orange-500/30',
}

export const STATUS_COLORS: Record<Status, string> = {
  passed: '#10b981',
  healed: '#38bdf8',
  failed: '#f43f5e',
  error: '#f97316',
}

export function Badge({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${className}`}>
      {children}
    </span>
  )
}

export const SeverityBadge = ({ severity }: { severity: Severity }) => (
  <Badge className={severityStyle[severity]}>{severity}</Badge>
)

export const StatusBadge = ({ status }: { status: Status }) => (
  <Badge className={statusStyle[status]}>{status === 'healed' ? 'passed (healed)' : status}</Badge>
)

export function Stat({ label, value, hint, accent = 'text-white' }: { label: string; value: ReactNode; hint?: string; accent?: string }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`mt-1 text-3xl font-bold ${accent}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  )
}

export function Spinner() {
  return <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
}

export function ErrorBox({ message }: { message: string }) {
  if (!message) return null
  return <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-200">{message}</div>
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center gap-3 py-12 text-center">
      <div className="text-lg font-semibold">{title}</div>
      <div className="text-sm text-slate-400">{children}</div>
    </div>
  )
}
