export type AgentStreamMessage =
  | { type: 'log'; message: string }
  | { type: 'approval_request'; id: string; summary: string; detail: string }

export function connectAgentStream(
  onMessage: (msg: AgentStreamMessage) => void,
): { socket: WebSocket; respond: (id: string, approved: boolean) => void } {
  const socket = new WebSocket('ws://localhost:8000/ws/agent-stream')
  socket.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data) as AgentStreamMessage)
    } catch {
      // ignore malformed frames
    }
  }
  const respond = (id: string, approved: boolean) => {
    socket.send(JSON.stringify({ type: 'approval_response', id, approved }))
  }
  return { socket, respond }
}

const API_BASE = 'http://localhost:8000'

export async function createApp(prompt: string) {
  const res = await fetch(`${API_BASE}/apps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateApp(appId: string, prompt: string) {
  const res = await fetch(`${API_BASE}/apps/${appId}/prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function scanSandboxApp(appId: string) {
  const res = await fetch(`${API_BASE}/apps/${appId}/scan`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createEngagement(payload: {
  target: string
  authorized_by: string
  scope_notes: string
  confirmed: boolean
}) {
  const res = await fetch(`${API_BASE}/engagements`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function scanExternalTarget(engagementId: string) {
  const res = await fetch(`${API_BASE}/engagements/${engagementId}/scan`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
