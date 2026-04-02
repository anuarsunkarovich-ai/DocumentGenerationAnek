import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { AuthTokenResponse, User } from '@shared/api/contracts'

type SessionState = {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  activeOrganizationId: string | null
  hydrated: boolean
  setSession: (session: AuthTokenResponse) => void
  setUser: (user: User) => void
  setActiveOrganizationId: (organizationId: string) => void
  markHydrated: () => void
  clearSession: () => void
}

function pickDefaultOrganization(user: User) {
  const preferred =
    user.memberships.find((membership) => membership.is_active && membership.is_default) ??
    user.memberships.find((membership) => membership.is_active)

  return preferred?.organization_id ?? user.organization_id
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      activeOrganizationId: null,
      hydrated: false,
      setSession: (session) =>
        set({
          accessToken: session.access_token,
          refreshToken: session.refresh_token,
          user: session.user,
          activeOrganizationId: pickDefaultOrganization(session.user),
        }),
      setUser: (user) =>
        set((state) => ({
          user,
          activeOrganizationId: state.activeOrganizationId ?? pickDefaultOrganization(user),
        })),
      setActiveOrganizationId: (organizationId) =>
        set({
          activeOrganizationId: organizationId,
        }),
      markHydrated: () => set({ hydrated: true }),
      clearSession: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          activeOrganizationId: null,
        }),
    }),
    {
      name: 'protocol-session',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        activeOrganizationId: state.activeOrganizationId,
      }),
      onRehydrateStorage: () => (state) => {
        state?.markHydrated()
      },
    },
  ),
)
