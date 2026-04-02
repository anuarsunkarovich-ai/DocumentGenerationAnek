import { Building2 } from 'lucide-react'

import { useSessionStore } from '@entities/session/model/session.store'

export function OrganizationSwitcher() {
  const user = useSessionStore((state) => state.user)
  const activeOrganizationId = useSessionStore((state) => state.activeOrganizationId)
  const setActiveOrganizationId = useSessionStore((state) => state.setActiveOrganizationId)

  if (!user) {
    return null
  }

  return (
    <div className="entity-switcher">
      <Building2 size={18} />
      <div className="entity-switcher__meta">
        <span className="entity-switcher__label">Active entity</span>
        <select
          aria-label="Active organization"
          value={activeOrganizationId ?? ''}
          onChange={(event) => {
            setActiveOrganizationId(event.target.value)
          }}
        >
          {user.memberships
            .filter((membership) => membership.is_active)
            .map((membership) => (
              <option key={membership.id} value={membership.organization_id}>
                {membership.organization.name}
              </option>
            ))}
        </select>
      </div>
    </div>
  )
}
