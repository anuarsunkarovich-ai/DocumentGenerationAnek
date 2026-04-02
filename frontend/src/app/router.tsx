import {
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'

import { RootLayout } from '@app/root-layout'
import { DashboardApprovalsPage } from '@pages/dashboard/ui/dashboard-approvals-page'
import { DashboardDeveloperPage } from '@pages/dashboard/ui/dashboard-developer-page'
import { DashboardJobsPage } from '@pages/dashboard/ui/dashboard-jobs-page'
import { DashboardOrganizationPage } from '@pages/dashboard/ui/dashboard-organization-page'
import { DashboardTemplatesPage } from '@pages/dashboard/ui/dashboard-templates-page'
import { LandingPage } from '@pages/landing/ui/landing-page'

const rootRoute = createRootRoute({
  component: RootLayout,
})

const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: LandingPage,
})

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard',
  component: DashboardTemplatesPage,
})

const dashboardJobsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard/jobs',
  component: DashboardJobsPage,
})

const dashboardApprovalsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard/approvals',
  component: DashboardApprovalsPage,
})

const dashboardOrganizationRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard/organization',
  component: DashboardOrganizationPage,
})

const dashboardDeveloperRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard/developer',
  component: DashboardDeveloperPage,
})

const routeTree = rootRoute.addChildren([
  landingRoute,
  dashboardRoute,
  dashboardJobsRoute,
  dashboardApprovalsRoute,
  dashboardOrganizationRoute,
  dashboardDeveloperRoute,
])

export const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
  defaultPendingMs: 0,
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
