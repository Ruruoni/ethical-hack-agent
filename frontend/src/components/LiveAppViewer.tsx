import { MonitorPlay } from 'lucide-react'

interface Props {
  port: number | null
}

export default function LiveAppViewer({ port }: Props) {
  return (
    <div className="h-full flex flex-col bg-panel border border-panel-border rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-panel-border text-slate-200">
        <MonitorPlay size={18} />
        <h2 className="font-semibold">Live App Viewer</h2>
        {port && <span className="text-xs text-slate-500 ml-auto">localhost:{port}</span>}
      </div>
      <div className="flex-1 bg-slate-950">
        {port ? (
          <iframe
            title="live-app"
            src={`http://localhost:${port}`}
            className="w-full h-full border-0"
          />
        ) : (
          <div className="h-full flex items-center justify-center text-slate-500 text-sm">
            Create an app from the Prompter panel to preview it here.
          </div>
        )}
      </div>
    </div>
  )
}
