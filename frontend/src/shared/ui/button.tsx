import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link, type LinkProps } from '@tanstack/react-router'

import { cn } from '@shared/lib/cn'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

type ButtonBaseProps = {
  children: ReactNode
  variant?: ButtonVariant
  fullWidth?: boolean
  className?: string
}

type ButtonProps = ButtonBaseProps & ButtonHTMLAttributes<HTMLButtonElement>

type ButtonLinkProps = ButtonBaseProps & LinkProps

const variantMap: Record<ButtonVariant, string> = {
  primary: 'button-primary',
  secondary: 'button-secondary',
  ghost: 'button-ghost',
}

export function Button({
  children,
  variant = 'primary',
  fullWidth = false,
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn('button', variantMap[variant], fullWidth && 'button-full', className)}
      {...props}
    >
      {children}
    </button>
  )
}

export function ButtonLink({
  children,
  variant = 'primary',
  fullWidth = false,
  className,
  ...props
}: ButtonLinkProps) {
  return (
    <Link
      className={cn('button', variantMap[variant], fullWidth && 'button-full', className)}
      {...props}
    >
      {children}
    </Link>
  )
}
