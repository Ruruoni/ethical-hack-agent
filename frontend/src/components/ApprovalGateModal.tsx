import { ShieldCheck } from 'lucide-react'

export interface PendingApproval {
  id: string
  summary: string
  detail: string
}

interface Props {
  approval: PendingApproval | null
  onRespond: (id: string, approved: boolean) => void
}

export default function ApprovalGateModal({ approval, onRespond }: Props) {
  if (!approval) return null

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-panel border border-amber-500/50 rounded-lg p-6 max-w-lg w-full space-y-4 shadow-xl">
        <div className="flex items-center gap-2 text-amber-300">
          <ShieldCheck size={20} />
          <h3 className="font-semibold">Human Approval Required</h3>
        </div>
        <p className="text-sm text-slate-200">{approval.summary}</p>
        <pre className="text-xs text-slate-400 bg-slate-950 rounded-md p-3 max-h-40 overflow-y-auto whitespace-pre-wrap">
          {approval.detail}
        </pre>
        <div className="flex gap-3">
          <button
            onClick={() => onRespond(approval.id, true)}
            className="flex-1 bg-emerald-600 hover:bg-emerald-500 rounded-md py-2 text-sm font-medium"
          >
            Approve &amp; Execute
          </button>
          <button
            onClick={() => onRespond(approval.id, false)}
            className="flex-1 border border-panel-border hover:bg-slate-800 rounded-md py-2 text-sm font-medium"
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  )
}
