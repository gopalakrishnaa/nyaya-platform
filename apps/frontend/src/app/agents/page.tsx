import type { Metadata } from 'next'
import AgentBuilder from './AgentBuilder'

export const metadata: Metadata = {
  title: 'AI Agent Builder',
  description: 'Build and run low-cost multi-agent workflows with LangGraph.',
}

export default function AgentsPage() {
  return <AgentBuilder />
}
