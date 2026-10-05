import { useState } from 'react'
import { Terminal, Send, ShieldAlert } from 'lucide-react'
import { createApp, createEngagement, scanExternalTarget, scanSandboxApp, updateApp } from '../lib/ws'

interface Props {
  appId: string | null
  onAppCreated: (appId: string) => void
}

export default function PrompterConsole({ appId, onAppCreated }: Props) {
  const [prompt, setPrompt] = useState('')
  const [target, setTarget] = useState('')
  const [authorizedBy, setAuthorizedBy] = useState('')
  const [scopeNotes, setScopeNotes] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)

  async function handleSubmitPrompt() {
    if (!prompt.trim()) return
    setBusy(true)
    try {
      if (appId) {
        await updateApp(appId, prompt)
      } else {
        const { app_id } = await createApp(prompt)
        onAppCreated(app_id)
      }
      setPrompt('')
    } catch (err) {
      console.error(err)
    } finally {
      setBusy(false)
    }
  }

  async function handleScanSandbox() {
    if (!appId) return
    await scanSandboxApp(appId)
  }

  async function handleScanExternal() {
    if (!confirmed || !target.trim() || !authorizedBy.trim()) return
    const { engagement_id } = await createEngagement({
      target,
      authorized_by: authorizedBy,
      scope_notes: scopeNotes,
      confirmed,
    })
    await scanExternalTarget(engagement_id)
  }

  return (
    <div className="h-full flex flex-col bg-panel border border-panel-border rounded-lg p-4 gap-4 overflow-y-auto">
      <div className="flex items-center gap-2 text-slate-200">
        <Terminal size={18} />
        <h2 className="font-semibold">Prompter &amp; App Control</h2>
      </div>

      <div className="space-y-2">
        <textarea
          className="w-full h-28 bg-slate-900 border border-panel-border rounded-md p-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-sky-500"
          placeholder="Describe what to build or change, e.g. 'Add a secure cryptographic key monitoring panel'"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <button
          onClick={handleSubmitPrompt}
          disabled={busy || !prompt.trim()}
          className="w-full flex items-center justify-center gap-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-sm font-medium rounded-md py-2"
        >
          <Send size={14} />
          {appId ? 'Update App' : 'Create App'}
        </button>
        {appId && (
          <button
            onClick={handleScanSandbox}
            className="w-full text-sm rounded-md py-2 border border-panel-border hover:bg-slate-800"
          >
            Scan this app (sandboxed, own code only)
          </button>
        )}
      </div>

      <div className="border-t border-panel-border pt-4 space-y-2">
        <div className="flex items-center gap-2 text-slate-300 text-sm">
          <ShieldAlert size={16} className="text-amber-400" />
          <span className="font-medium">External target engagement</span>
        </div>
        <p className="text-xs text-slate-500">
          Only scan hosts you own or are explicitly authorized to test. Recon and
          confirmation checks are passive/non-destructive only.
        </p>
        <input
          className="w-full bg-slate-900 border border-panel-border rounded-md p-2 text-sm"
          placeholder="Target host or URL"
          value={target}
          onChange={(e) => setTarget(e.target.value)}
        />
        <input
          className="w-full bg-slate-900 border border-panel-border rounded-md p-2 text-sm"
          placeholder="Who is authorizing this test? (e.g. 'I own this host')"
          value={authorizedBy}
          onChange={(e) => setAuthorizedBy(e.target.value)}
        />
        <input
          className="w-full bg-slate-900 border border-panel-border rounded-md p-2 text-sm"
          placeholder="Scope notes (optional)"
          value={scopeNotes}
          onChange={(e) => setScopeNotes(e.target.value)}
        />
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
          I confirm I own this target or have written authorization to test it.
        </label>
        <button
          onClick={handleScanExternal}
          disabled={!confirmed || !target.trim() || !authorizedBy.trim()}
          className="w-full text-sm rounded-md py-2 border border-amber-500/40 text-amber-300 hover:bg-amber-500/10 disabled:opacity-40"
        >
          Start authorized recon
        </button>
      </div>
    </div>
  )
}
