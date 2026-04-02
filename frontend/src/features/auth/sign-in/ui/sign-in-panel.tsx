import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { useSessionStore } from '@entities/session/model/session.store'
import { runtimeApi } from '@shared/api/runtime-api'
import { ApiError } from '@shared/api/http-client'
import { Button } from '@shared/ui/button'

const signInSchema = z.object({
  email: z.string().email('Enter a valid email.'),
  password: z.string().min(1, 'Enter your password.'),
})

type SignInValues = z.infer<typeof signInSchema>

const defaultValues: SignInValues = {
  email: '',
  password: '',
}

export function SignInPanel() {
  const setSession = useSessionStore((state) => state.setSession)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues,
  })

  const signInMutation = useMutation({
    mutationFn: (values: SignInValues) => runtimeApi.login(values),
    onSuccess: (session) => {
      setSession(session)
    },
    onError: (error) => {
      const message =
        error instanceof ApiError ? error.detail : 'Could not connect to the backend right now.'

      setError('root', {
        message,
      })
    },
  })

  return (
    <form className="login-panel" onSubmit={handleSubmit((values) => signInMutation.mutate(values))}>
      <div className="field-grid">
        <label className="field-label">
          Email
          <input placeholder="admin@protocol.kz" {...register('email')} />
          {errors.email ? <span className="field-error">{errors.email.message}</span> : null}
        </label>
        <label className="field-label">
          Password
          <input placeholder="Strong password" type="password" {...register('password')} />
          {errors.password ? <span className="field-error">{errors.password.message}</span> : null}
        </label>
      </div>

      {errors.root?.message ? (
        <div className="form-feedback form-feedback--error">{errors.root.message}</div>
      ) : null}

      <Button disabled={signInMutation.isPending} fullWidth type="submit">
        {signInMutation.isPending ? 'Connecting...' : 'Connect live backend'}
      </Button>
    </form>
  )
}
