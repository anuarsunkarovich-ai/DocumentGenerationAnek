import { useQuery } from '@tanstack/react-query'

import { runtimeApi } from '@shared/api/runtime-api'
import { LoadingState } from '@shared/ui/loading-state'
import { ConciergeSection } from '@widgets/marketing/concierge-section'
import { ExpertiseSection } from '@widgets/marketing/expertise-section'
import { HeroSection } from '@widgets/marketing/hero-section'
import { PricingSection } from '@widgets/marketing/pricing-section'
import { ProofSection } from '@widgets/marketing/proof-section'
import { SiteFooter } from '@widgets/marketing/site-footer'
import { SiteHeader } from '@widgets/marketing/site-header'

export function LandingPage() {
  const pulseQuery = useQuery({
    queryKey: ['system-pulse'],
    queryFn: () => runtimeApi.getSystemPulse(),
  })

  return (
    <>
      <SiteHeader />

      <main>
        {pulseQuery.data ? (
          <HeroSection pulse={pulseQuery.data} />
        ) : (
          <div className="page-shell">
            <LoadingState />
          </div>
        )}
        <ProofSection />
        <ExpertiseSection />
        <ConciergeSection />
        <PricingSection />
      </main>

      <SiteFooter />
    </>
  )
}
