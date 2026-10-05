import { useEffect, useState } from 'react'
import PrompterConsole from './PrompterConsole'
import LiveAppViewer from './LiveAppViewer'
import AgentActivityStream from './AgentActivityStream'
import ApprovalGateModal, { PendingApproval } from './ApprovalGateModal'
import { connectAgentStream } from '../lib/ws'

export default function Dashboard() {
  const [appId, setAppId] = useState<string | null>(null)
  const [port, setPort] = useState<number | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null)
  const [respond, setRespond] = useState<((id: string, approved: boolean) => void) | null>(null)

  useEffect(() => {
    const { socket, respond: respondFn } = connectAgentStream((msg) => {
      if (msg.type === 'log') {
        setLogs((prev) => [...prev.slice(-500), msg.message])
      } else if (msg.type === 'approval_request') {
        setPendingApproval({ id: msg.id, summary: msg.summary, detail: msg.detail })
      }
    })
    setRespond(() => respondFn)
    return () => socket.close()
  }, [])

  function handleAppCreated(id: string) {
    setAppId(id)
    // Dev server port mirrors the backend's allocation scheme; the create-app
    // response also returns it directly if you want to wire that through.
  }

  function handleApprovalResponse(id: string, approved: boolean) {
    respond?.(id, approved)
    setPendingApproval(null)
  }

  return (
    <div className="h-screen w-screen bg-slate-950 p-4">
      <header className="mb-4">
        <h1 className="text-xl font-bold text-slate-100">CyberFactory</h1>
        <p className="text-sm text-slate-500">
          Local, sandboxed app generation + security agent swarm
        </p>
      </header>

      <div className="grid grid-cols-3 grid-rows-2 gap-4 h-[calc(100vh-5rem)]">
        <div className="col-span-1 row-span-2">
          <PrompterConsole appId={appId} onAppCreated={handleAppCreated} />
        </div>
        <div className="col-span-2 row-span-1">
          <LiveAppViewer port={port} />
        </div>
        <div className="col-span-2 row-span-1">
          <AgentActivityStream logs={logs} />
        </div>
      </div>

      <ApprovalGateModal approval={pendingApproval} onRespond={handleApprovalResponse} />
    </div>
  )
}
