import { create } from 'zustand'

export type TrackedJobItem = {
  id: string
  recipient: string
  recipient_meta: string
  status: string
  document_name: string
  created_at: string
}

type LiveJobState = {
  items: TrackedJobItem[]
  upsertJob: (job: TrackedJobItem) => void
  clearJobs: () => void
}

export const useLiveJobStore = create<LiveJobState>((set) => ({
  items: [],
  upsertJob: (job) =>
    set((state) => {
      const existing = state.items.find((item) => item.id === job.id)

      if (!existing) {
        return {
          items: [job, ...state.items].slice(0, 20),
        }
      }

      return {
        items: state.items
          .map((item) => (item.id === job.id ? { ...item, ...job } : item))
          .sort((left, right) => right.created_at.localeCompare(left.created_at)),
      }
    }),
  clearJobs: () => set({ items: [] }),
}))
