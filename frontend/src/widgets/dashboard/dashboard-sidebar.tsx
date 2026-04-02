import {
  Activity,
  Building2,
  ClipboardList,
  KeyRound,
  LayoutTemplate,
  ShieldCheck,
} from 'lucide-react'
import { Link, useRouterState } from '@tanstack/react-router'

import { useSessionStore } from '@entities/session/model/session.store'
import { cn } from '@shared/lib/cn'

const navItems = [
  { label: 'Template Library', icon: LayoutTemplate, to: '/dashboard' },
  { label: 'Job Queue', icon: ClipboardList, to: '/dashboard/jobs' },
  { label: 'Approval Workflow', icon: ShieldCheck, to: '/dashboard/approvals' },
  { label: 'Organization Settings', icon: Building2, to: '/dashboard/organization' },
  { label: 'API & Developer Hub', icon: KeyRound, to: '/dashboard/developer' },
] as const

export function DashboardSidebar() {
  const user = useSessionStore((state) => state.user)
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })
  const initials = user?.full_name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <aside className="dashboard-sidebar">
      <div className="dashboard-sidebar__brand">
        <div className="brand newsreader">Protocol Suite</div>
        <div className="dashboard-sidebar__status">
          <Activity size={14} />
          <span>Enterprise core v8.1</span>
        </div>
      </div>

      <nav className="dashboard-nav" aria-label="Dashboard">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive =
            pathname === item.to ||
            (item.to !== '/dashboard' && pathname.startsWith(`${item.to}/`))

          return (
            <Link
              className={cn('dashboard-nav__item', isActive && 'is-active')}
              key={item.label}
              to={item.to}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="dashboard-profile">
        <span className="avatar">{initials ?? 'PR'}</span>
        <div>
          <p style={{ margin: 0, fontWeight: 700 }}>{user?.full_name ?? 'Protocol Operator'}</p>
          <p className="micro-label" style={{ margin: '4px 0 0' }}>
            {user ? 'Senior legal counsel' : 'Prototype access'}
          </p>
        </div>
      </div>
    </aside>
  )
}
