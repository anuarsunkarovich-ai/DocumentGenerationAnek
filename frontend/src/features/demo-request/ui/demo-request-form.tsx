import { startTransition, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'

import {
  demoRequestSchema,
  type DemoRequestFormValues,
} from '@features/demo-request/model/schema'
import { Button } from '@shared/ui/button'

const defaultValues: DemoRequestFormValues = {
  fullName: '',
  company: '',
  email: '',
  monthlyVolume: '',
  notes: '',
}

export function DemoRequestForm() {
  const [submitted, setSubmitted] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<DemoRequestFormValues>({
    resolver: zodResolver(demoRequestSchema),
    defaultValues,
  })

  const onSubmit = async (values: DemoRequestFormValues) => {
    await new Promise((resolve) => setTimeout(resolve, 500))
    startTransition(() => {
      setSubmitted(true)
    })
    reset(values)
  }

  return (
    <form className="form-panel" onSubmit={handleSubmit(onSubmit)}>
      <div className="field-grid field-grid--two">
        <label className="field-label">
          Contact
          <input placeholder="Anek" {...register('fullName')} />
          {errors.fullName ? <span className="field-error">{errors.fullName.message}</span> : null}
        </label>
        <label className="field-label">
          Firm
          <input placeholder="Astana Realty Group" {...register('company')} />
          {errors.company ? <span className="field-error">{errors.company.message}</span> : null}
        </label>
      </div>

      <div className="field-grid field-grid--two">
        <label className="field-label">
          Work Email
          <input placeholder="operations@firm.kz" {...register('email')} />
          {errors.email ? <span className="field-error">{errors.email.message}</span> : null}
        </label>
        <label className="field-label">
          Monthly Volume
          <select {...register('monthlyVolume')}>
            <option value="">Select volume</option>
            <option value="up-to-100">Up to 100 documents</option>
            <option value="100-500">100-500 documents</option>
            <option value="500-plus">500+ documents</option>
          </select>
          {errors.monthlyVolume ? (
            <span className="field-error">{errors.monthlyVolume.message}</span>
          ) : null}
        </label>
      </div>

      <label className="field-label">
        Workflow Notes
        <textarea
          placeholder="Tell us which contracts, acts, approvals, or compliance packs you need automated."
          {...register('notes')}
        />
        {errors.notes ? <span className="field-error">{errors.notes.message}</span> : null}
      </label>

      {submitted ? (
        <div className="form-feedback form-feedback--success">
          Proposal request staged. For the real launch, wire this form to Telegram, email, or
          your CRM inbox.
        </div>
      ) : null}

      <Button disabled={isSubmitting} fullWidth type="submit">
        {isSubmitting ? 'Preparing proposal...' : 'Request proposal'}
      </Button>
    </form>
  )
}
