import { z, type ZodType } from 'zod'

import { useSessionStore } from '@entities/session/model/session.store'
import { authTokenResponseSchema } from '@shared/api/contracts'
import { env } from '@shared/config/env'

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: BodyInit | Record<string, unknown>
  auth?: boolean
  headers?: HeadersInit
}

const emptySchema = z.unknown()

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

export class HttpClient {
  private readonly baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  async get<T>(path: string, schema: ZodType<T>): Promise<T> {
    return this.request(path, { method: 'GET' }, schema)
  }

  async post<T>(path: string, body: RequestOptions['body'], schema: ZodType<T>) {
    return this.request(path, { method: 'POST', body }, schema)
  }

  async request<T>(
    path: string,
    options: RequestOptions,
    schema: ZodType<T> = emptySchema as ZodType<T>,
    retrying = false,
  ): Promise<T> {
    const session = useSessionStore.getState()
    const headers = new Headers(options.headers)
    const requestInit: RequestInit = {
      method: options.method ?? 'GET',
      headers,
    }

    if (options.auth !== false && session.accessToken) {
      headers.set('Authorization', `Bearer ${session.accessToken}`)
    }

    if (options.body instanceof FormData || options.body instanceof URLSearchParams) {
      requestInit.body = options.body
    } else if (options.body !== undefined) {
      headers.set('Content-Type', 'application/json')
      requestInit.body = JSON.stringify(options.body)
    }

    const response = await fetch(`${this.baseUrl}${path}`, requestInit)

    if (response.status === 401 && !retrying && session.refreshToken) {
      const refreshed = await this.refresh(session.refreshToken)

      if (refreshed) {
        return this.request(path, options, schema, true)
      }
    }

    const isJson = response.headers.get('content-type')?.includes('application/json')
    const payload = isJson ? await response.json() : await response.text()

    if (!response.ok) {
      const detail =
        typeof payload === 'string'
          ? payload
          : payload && typeof payload === 'object' && 'detail' in payload
            ? String(payload.detail)
            : 'Request failed.'

      throw new ApiError(response.status, detail)
    }

    return schema.parse(payload)
  }

  private async refresh(refreshToken: string) {
    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!response.ok) {
        useSessionStore.getState().clearSession()
        return false
      }

      const payload = authTokenResponseSchema.parse(await response.json())
      useSessionStore.getState().setSession(payload)
      return true
    } catch {
      if (env.apiMode === 'live') {
        useSessionStore.getState().clearSession()
      }
      return false
    }
  }
}

export const httpClient = new HttpClient(env.apiBaseUrl)
