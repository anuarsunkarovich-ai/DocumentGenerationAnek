import { z } from 'zod'

export const quickGenerationFormSchema = z.object({
  templateId: z.string().min(1, 'Pick a template.'),
  recipient: z.string().min(2, 'Add a recipient or counterparty.'),
  recipientRole: z.string().min(2, 'Add department, company, or role.'),
  documentType: z.string().min(2, 'Tell the engine what to generate.'),
})

export type QuickGenerationFormValues = z.infer<typeof quickGenerationFormSchema>
