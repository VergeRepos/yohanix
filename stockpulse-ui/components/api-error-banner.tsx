import React from "react";

interface ApiErrorBannerProps {
  error: string;
  title?: string;
}

export function ApiErrorBanner({ error, title = "Dashboard" }: ApiErrorBannerProps) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <div className="glass-card p-6 border border-red-500/30 bg-red-950/20 text-red-300 space-y-4">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <h2 className="font-semibold text-lg">Failed to connect to Yohanix API</h2>
            <p className="text-sm text-slate-400">
              Could not reach the FastAPI backend at <code className="bg-slate-900 px-1.5 py-0.5 rounded text-violet-300 font-mono">http://localhost:18000</code>. ({error})
            </p>
          </div>
        </div>
        <div className="bg-slate-900/80 p-4 rounded-lg space-y-2 text-sm font-mono text-slate-300">
          <p className="text-slate-400 font-sans text-xs uppercase tracking-wider">How to resolve:</p>
          <p>1. Open a terminal in your project root.</p>
          <p>2. Start the FastAPI backend server:</p>
          <div className="bg-black/60 p-2 rounded text-green-400 select-all">make api</div>
          <p className="text-xs text-slate-400 font-sans">
            Or manually: <code className="text-slate-300">python -m uvicorn stockpulse.api.server:app --port 18000 --reload</code>
          </p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-md text-sm font-medium transition-colors"
        >
          Retry Connection
        </button>
      </div>
    </div>
  );
}
