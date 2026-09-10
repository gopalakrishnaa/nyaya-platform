import { Annotation, END, START, StateGraph } from '@langchain/langgraph'
import { generateText } from 'ai'
import { google } from '@ai-sdk/google'
import { anthropic } from '@ai-sdk/anthropic'
import { z } from 'zod'

export const agentRoleSchema = z.object({
  id: z.string().trim().min(1).max(40),
  name: z.string().trim().min(2).max(60),
  role: z.string().trim().min(3).max(100),
  instructions: z.string().trim().min(10).max(2_000),
})

export const runAgentSchema = z.object({
  name: z.string().trim().min(2).max(80),
  objective: z.string().trim().min(5).max(2_000),
  input: z.string().trim().min(1).max(12_000),
  provider: z.enum(['demo', 'nvidia', 'google', 'anthropic']).default('demo'),
  model: z.string().trim().min(1).max(100),
  maxSteps: z.number().int().min(1).max(6).default(3),
  maxBudgetUsd: z.number().min(0).max(5).default(0.05),
  agents: z.array(agentRoleSchema).min(1).max(6),
})

export type AgentBuilderRun = z.infer<typeof runAgentSchema>

export interface AgentTrace {
  agentId: string
  agentName: string
  role: string
  output: string
  inputTokens: number
  outputTokens: number
  estimatedCostUsd: number
  durationMs: number
}

export interface AgentRunResult {
  runId: string
  output: string
  traces: AgentTrace[]
  totalInputTokens: number
  totalOutputTokens: number
  estimatedCostUsd: number
  stoppedForBudget: boolean
}

const MODEL_PRICES: Record<string, { input: number; output: number }> = {
  // USD per million tokens. Estimates only; providers may change pricing.
  'gemini-2.5-flash-lite': { input: 0.1, output: 0.4 },
  'gemini-3.1-flash-lite': { input: 0.25, output: 1.5 },
  'claude-3-5-haiku-20241022': { input: 0.8, output: 4 },
  // build.nvidia.com currently describes this as a free prototype endpoint.
  'nvidia/nemotron-3-ultra-550b-a55b': { input: 0, output: 0 },
}

const BuilderState = Annotation.Root({
  config: Annotation<AgentBuilderRun>(),
  step: Annotation<number>(),
  latest: Annotation<string>(),
  traces: Annotation<AgentTrace[]>({
    reducer: (left, right) => left.concat(right),
    default: () => [],
  }),
  spent: Annotation<number>(),
  stoppedForBudget: Annotation<boolean>(),
})

function estimateTokens(text: string): number {
  return Math.max(1, Math.ceil(text.length / 4))
}

function estimateCost(model: string, inputTokens: number, outputTokens: number): number {
  const price = MODEL_PRICES[model] ?? { input: 1, output: 5 }
  return (inputTokens * price.input + outputTokens * price.output) / 1_000_000
}

function demoOutput(config: AgentBuilderRun, step: number, previous: string): string {
  const agent = config.agents[step]
  const context = previous === config.input ? config.input : previous
  if (step === config.agents.length - 1 || step === config.maxSteps - 1) {
    return `Demo result for “${config.objective}”\n\n${agent.name} (${agent.role}) reviewed the supplied input and produced this concise handoff:\n\n${context.slice(0, 900)}${context.length > 900 ? '…' : ''}\n\nConnect a Google or Anthropic key to replace this deterministic preview with a live model response.`
  }
  return `${agent.name} — ${agent.role}\n\nKey working notes for the next agent:\n${context.slice(0, 700)}${context.length > 700 ? '…' : ''}`
}

async function runModel(config: AgentBuilderRun, system: string, prompt: string) {
  if (config.provider === 'demo') {
    return { text: '', inputTokens: estimateTokens(system + prompt), outputTokens: 0 }
  }

  if (config.provider === 'nvidia') {
    const response = await fetch('https://integrate.api.nvidia.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.NVIDIA_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: config.model,
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: prompt },
        ],
        temperature: 0.2,
        top_p: 0.95,
        max_tokens: 900,
        stream: false,
        chat_template_kwargs: { enable_thinking: false },
      }),
      signal: AbortSignal.timeout(45_000),
    })
    if (!response.ok) {
      const message = await response.text()
      throw new Error(`NVIDIA NIM request failed (${response.status}): ${message.slice(0, 300)}`)
    }
    const data = await response.json() as {
      choices?: Array<{ message?: { content?: string } }>
      usage?: { prompt_tokens?: number; completion_tokens?: number }
    }
    const text = data.choices?.[0]?.message?.content?.trim() ?? ''
    if (!text) throw new Error('NVIDIA NIM returned an empty response.')
    return {
      text,
      inputTokens: data.usage?.prompt_tokens ?? estimateTokens(system + prompt),
      outputTokens: data.usage?.completion_tokens ?? estimateTokens(text),
    }
  }

  const model = config.provider === 'google'
    ? google(config.model)
    : anthropic(config.model)
  const result = await generateText({
    model,
    system,
    prompt,
    maxOutputTokens: 900,
    temperature: 0.2,
    maxRetries: 1,
    timeout: 30_000,
  })
  return {
    text: result.text,
    inputTokens: result.usage.inputTokens ?? estimateTokens(system + prompt),
    outputTokens: result.usage.outputTokens ?? estimateTokens(result.text),
  }
}

export async function runAgentBuilder(config: AgentBuilderRun): Promise<AgentRunResult> {
  const work = async (state: typeof BuilderState.State) => {
    const agent = state.config.agents[state.step]
    const started = Date.now()
    const system = `You are ${agent.name}, acting as ${agent.role}.\n\n${agent.instructions}\n\nWork only toward this objective: ${state.config.objective}. Be concise. Do not claim that you used tools or sources that were not provided. Your output will be handed to the next agent, unless you are the final agent.`
    const prompt = `Original input:\n${state.config.input}\n\nPrevious agent output:\n${state.latest}\n\nComplete your part of the workflow now.`

    const projectedInput = estimateTokens(system + prompt)
    const projectedCost = estimateCost(state.config.model, projectedInput, 900)
    if (state.config.provider !== 'demo' && state.spent + projectedCost > state.config.maxBudgetUsd) {
      return { stoppedForBudget: true }
    }

    const response = await runModel(state.config, system, prompt)
    const text = state.config.provider === 'demo'
      ? demoOutput(state.config, state.step, state.latest)
      : response.text
    const outputTokens = state.config.provider === 'demo' ? estimateTokens(text) : response.outputTokens
    const cost = state.config.provider === 'demo'
      ? 0
      : estimateCost(state.config.model, response.inputTokens, outputTokens)

    const trace: AgentTrace = {
      agentId: agent.id,
      agentName: agent.name,
      role: agent.role,
      output: text,
      inputTokens: response.inputTokens,
      outputTokens,
      estimatedCostUsd: cost,
      durationMs: Date.now() - started,
    }
    return {
      latest: text,
      step: state.step + 1,
      spent: state.spent + cost,
      traces: [trace],
    }
  }

  const route = (state: typeof BuilderState.State) => {
    const finished = state.stoppedForBudget
      || state.step >= state.config.maxSteps
      || state.step >= state.config.agents.length
    return finished ? END : 'work'
  }

  const graph = new StateGraph(BuilderState)
    .addNode('work', work)
    .addEdge(START, 'work')
    .addConditionalEdges('work', route, ['work', END])
    .compile()

  const result = await graph.invoke({
    config,
    step: 0,
    latest: config.input,
    traces: [],
    spent: 0,
    stoppedForBudget: false,
  }, { recursionLimit: 12 })

  return {
    runId: crypto.randomUUID(),
    output: result.latest,
    traces: result.traces,
    totalInputTokens: result.traces.reduce((sum, trace) => sum + trace.inputTokens, 0),
    totalOutputTokens: result.traces.reduce((sum, trace) => sum + trace.outputTokens, 0),
    estimatedCostUsd: result.spent,
    stoppedForBudget: result.stoppedForBudget,
  }
}
