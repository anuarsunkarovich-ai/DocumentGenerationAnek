import { Bell, Plus, Search } from 'lucide-react'

import { OrganizationSwitcher } from '@features/organization-switcher/ui/organization-switcher'
import { useDashboardUiStore } from '@pages/dashboard/model/dashboard-ui.store'
import { ButtonLink } from '@shared/ui/button'

export function DashboardTopbar() {
  const search = useDashboardUiStore((state) => state.search)
  const setSearch = useDashboardUiStore((state) => state.setSearch)

  return (
    <header className="dashboard-topbar">
      <div className="dashboard-topbar__left">
        <OrganizationSwitcher />
        <label className="search-shell">
          <Search size={16} />
          <input
            aria-label="Search templates"
            placeholder="Search archive, templates, or recipients..."
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
            }}
          />
        </label>
      </div>

      <div className="dashboard-topbar__right">
        <ButtonLink to="/" variant="secondary">
          Back to site
        </ButtonLink>
        <ButtonLink className="button-full-mobile" to="/dashboard/jobs" variant="primary">
          <Plus size={16} />
          Initiate new document
        </ButtonLink>
        <ButtonLink to="/dashboard/approvals" variant="secondary">
          <Bell size={16} />
        </ButtonLink>
      </div>
    </header>
  )
}
