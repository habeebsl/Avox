import z from 'zod'

export const sentenceAlignment = z.object({
    text: z.string(),
    start: z.float64(),
    end: z.float64()

}).strip()

export const insight = z.object({
    insight: z.string(),
    explanation: z.string()
}).strip()

const Step = z.union([
    z.literal("speech"), 
    z.literal("merged"),
    z.literal("insights"),
    z.literal("transcript"),
    z.literal("music")
]) 

export const ResponsePayload = z.object({
    type: z.union([
        z.literal("speech"), 
        z.literal("merged"), 
        z.literal("insight"), 
        z.literal("done"), 
        z.literal("error"),
        z.literal("fatal_error"),
        z.literal("complete"),
        z.literal("received"),
        z.literal("audio_complete")  // New combined audio message type
    ]),
    message: z.string().optional(),
    index: z.number().optional(),
    step: Step.optional(),
    transcript: z.string().optional(),
    translations: z.array(z.string()).optional().nullable(),
    alignments: z.array(sentenceAlignment).optional(),
    insights: z.array(insight).optional()
}).strip()


export const InsightsResponsePayload = z.object({
    type: z.literal("insight"),
    index: z.number(),
    insights: z.array(insight)
}).strip()

export const SpeechResponsePayload = z.object({
    type: z.literal("speech"),
    index: z.number(),
    transcript: z.string(),
    translations: z.array(z.string()).nullable(),
    alignments: z.array(sentenceAlignment)
}).strip()

export const FinishedAdPayload = z.object({
    type: z.literal("done"),
    index: z.number()
}).strip()

export const MergedAdPayload = z.object({
    type: z.literal("merged"),
    index: z.number()
}).strip()

export const AudioCompletePayload = z.object({
    type: z.literal("audio_complete"),
    index: z.number(),
    transcript: z.string(),
    translations: z.array(z.string()).nullable(),
    alignments: z.array(sentenceAlignment)
}).strip()

export const AdErrorPayload = z.object({
    type: z.literal("error"),
    step: Step,
    index: z.number(),
    message: z.string()
}).strip()