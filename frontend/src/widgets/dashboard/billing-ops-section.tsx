import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { runtimeApi } from '@shared/api/runtime-api'
import { Button } from '@shared/ui/button'
import { JsonPreview } from '@shared/ui/json-preview'

type BillingOpsSectionProps = {
  organizationId: string
}

export function BillingOpsSection({ organizationId }: BillingOpsSectionProps) {
  const [targetPlanCode, setTargetPlanCode] = useState('growth')
  const [result, setResult] = useState<unknown>(null)

  const plansQuery = useQuery({
    queryKey: ['billing-plans', organizationId],
    queryFn: () => runtimeApi.listBillingPlans(organizationId),
    enabled: Boolean(organizationId),
  })

  const invoicesQuery = useQuery({
    queryKey: ['billing-invoices', organizationId],
    queryFn: () => runtimeApi.listBillingInvoices(organizationId, 10),
    enabled: Boolean(organizationId),
  })

  const changeMutation = useMutation({
    mutationFn: () =>
      runtimeApi.changeSubscription({
        organization_id: organizationId,
        target_plan_code: targetPlanCode,
      }),
    onSuccess: setResult,
  })

  const cycleMutation = useMutation({
    mutationFn: () =>
      runtimeApi.runBillingCycle({
        organization_id: organizationId,
      }),
    onSuccess: setResult,
  })

  return (
    <section className="ops-section" id="billing-control">
      <div className="data-card">
        <div className="data-card__header">
          <div>
            <p className="micro-label">Plans, invoices, subscription control</p>
            <h2 className="newsreader">Billing Control</h2>
          </div>
        </div>

        <div className="ops-grid">
          <div className="ops-panel">
            <label className="field-label">
              Target plan
              <select value={targetPlanCode} onChange={(event) => setTargetPlanCode(event.target.value)}>
                {plansQuery.data?.items.map((plan) => (
                  <option key={plan.id} value={plan.code}>
                    {plan.name}
                  </option>
                ))}
              </select>
            </label>

            <div className="ops-button-row">
              <Button type="button" onClick={() => changeMutation.mutate()}>
                Schedule plan change
              </Button>
              <Button type="button" variant="secondary" onClick={() => cycleMutation.mutate()}>
                Run billing cycle
              </Button>
            </div>

            {plansQuery.data ? <JsonPreview title="Plan catalog" payload={plansQuery.data} /> : null}
          </div>

          <div className="ops-panel">
            {invoicesQuery.data ? (
              <JsonPreview title="Recent invoices" payload={invoicesQuery.data} />
            ) : null}
          </div>
        </div>

        {result ? <JsonPreview title="Last billing operation" payload={result} /> : null}
      </div>
    </section>
  )
}
