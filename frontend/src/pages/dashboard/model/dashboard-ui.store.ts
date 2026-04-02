import { create } from 'zustand'

type DashboardUiState = {
  search: string
  setSearch: (value: string) => void
}

export const useDashboardUiStore = create<DashboardUiState>((set) => ({
  search: '',
  setSearch: (value) => set({ search: value }),
}))
