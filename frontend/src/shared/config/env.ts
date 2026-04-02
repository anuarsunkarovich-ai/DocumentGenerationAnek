import { z } from 'zod'

const rawEnvSchema = z.object({
  VITE_API_MODE: z.enum(['mock', 'live']).optional(),
  VITE_API_BASE_URL: z.string().optional(),
})

const parsed = rawEnvSchema.parse(import.meta.env)

export const env = {
  apiMode: parsed.VITE_API_MODE ?? 'mock',
  apiBaseUrl: parsed.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
} as const
