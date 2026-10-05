import { useEffect, useRef } from 'react'
import { Activity } from 'lucide-react'

interface Props {
  logs: string[]
}

export default function AgentActivityStream({ logs }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="h-full flex flex-col bg-panel border border-panel-border rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-panel-border text-slate-200">
        <Activity size={18} />
        <h2 className="font-semibold">Agent Thought &amp; Activity Stream</h2>
      </div>
      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-1 bg-slate-950">
        {logs.length === 0 && <p className="text-slate-600">Waiting for agent activity...</p>}
        {logs.map((line, i) => (
          <p key={i} className="text-slate-300 whitespace-pre-wrap">
            {line}
          </p>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
