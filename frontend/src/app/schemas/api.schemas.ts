import z from 'zod'

export const CloningSentencesPayload = z.object({
    sentences: z.array(z.string()),
    language: z.string()
}).strip()

export const ReservationIdPayload = z.object({
    reservation_id: z.string().optional(),
    created: z.boolean(),
    detail: z.string().optional()
}).strip()