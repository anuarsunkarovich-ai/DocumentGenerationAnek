import { useEffect } from 'react'

import { runtimeApi } from '@shared/api/runtime-api'
import { env } from '@shared/config/env'
import { useSessionStore } from '@entities/session/model/session.store'

export function useSessionBootstrap() {
  const hydrated = useSessionStore((state) => state.hydrated)
  const accessToken = useSessionStore((state) => state.accessToken)
  const setSession = useSessionStore((state) => state.setSession)
  const setUser = useSessionStore((state) => state.setUser)
  const clearSession = useSessionStore((state) => state.clearSession)

  useEffect(() => {
    if (!hydrated) {
      return
    }

    if (env.apiMode === 'mock') {
      if (!accessToken) {
        void runtimeApi.getDemoSession().then((session) => {
          setSession(session)
        })
      }

      return
    }

    if (!accessToken) {
      return
    }

    void runtimeApi
      .getCurrentUser()
      .then((user) => {
        setUser(user)
      })
      .catch(() => {
        clearSession()
      })
  }, [accessToken, clearSession, hydrated, setSession, setUser])
}
