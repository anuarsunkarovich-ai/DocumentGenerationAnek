import { z } from 'zod'

export const demoRequestSchema = z.object({
  fullName: z.string().min(2, 'Tell us who should receive the proposal.'),
  company: z.string().min(2, 'Add the firm or agency name.'),
  email: z.string().email('Use a valid work email.'),
  monthlyVolume: z.string().min(1, 'Select an expected document volume.'),
  notes: z.string().min(12, 'Add a little context so the proposal feels bespoke.'),
})

export type DemoRequestFormValues = z.infer<typeof demoRequestSchema>
