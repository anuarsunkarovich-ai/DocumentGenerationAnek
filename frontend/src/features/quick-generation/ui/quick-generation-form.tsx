import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'

import {
  quickGenerationFormSchema,
  type QuickGenerationFormValues,
} from '@features/quick-generation/model/schema'
import { dashboardQueryKeys } from '@pages/dashboard/model/queries'
import type { Template } from '@shared/api/contracts'
import { runtimeApi } from '@shared/api/runtime-api'
import { Button } from '@shared/ui/button'

type QuickGenerationFormProps = {
  organizationId: string
  templates: Template[]
}

export function QuickGenerationForm({
  organizationId,
  templates,
}: QuickGenerationFormProps) {
  const queryClient = useQueryClient()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<QuickGenerationFormValues>({
    resolver: zodResolver(quickGenerationFormSchema),
    defaultValues: {
      templateId: templates[0]?.id ?? '',
      recipient: '',
      recipientRole: '',
      documentType: '',
    },
  })

  const mutation = useMutation({
    mutationFn: (values: QuickGenerationFormValues) => runtimeApi.createQuickGeneration(values),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dashboardQueryKeys.jobQueue(organizationId),
      })
      void queryClient.invalidateQueries({
        queryKey: dashboardQueryKeys.audit(organizationId),
      })
      reset({
        templateId: templates[0]?.id ?? '',
        recipient: '',
        recipientRole: '',
        documentType: '',
      })
    },
  })

  return (
    <form className="form-panel" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
      <div className="field-grid">
        <label className="field-label">
          Template
          <select {...register('templateId')}>
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </select>
          {errors.templateId ? (
            <span className="field-error">{errors.templateId.message}</span>
          ) : null}
        </label>
      </div>

      <div className="field-grid field-grid--two">
        <label className="field-label">
          Recipient
          <input placeholder="Astana Central Real Estate" {...register('recipient')} />
          {errors.recipient ? <span className="field-error">{errors.recipient.message}</span> : null}
        </label>

        <label className="field-label">
          Recipient Meta
          <input placeholder="Legal admin / B2B holding" {...register('recipientRole')} />
          {errors.recipientRole ? (
            <span className="field-error">{errors.recipientRole.message}</span>
          ) : null}
        </label>
      </div>

      <label className="field-label">
        Document Type
        <input placeholder="Commercial lease addendum" {...register('documentType')} />
        {errors.documentType ? (
          <span className="field-error">{errors.documentType.message}</span>
        ) : null}
      </label>

      <Button disabled={mutation.isPending} fullWidth type="submit">
        {mutation.isPending ? 'Generating...' : 'Initiate new document'}
      </Button>
    </form>
  )
}
