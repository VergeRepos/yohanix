"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function UiSettingsPage() {
  const [pollingInterval, setPollingInterval] = useState<string>("15");
  const [animationsEnabled, setAnimationsEnabled] = useState<boolean>(true);
  const [compactView, setCompactView] = useState<boolean>(false);
  const [saved, setSaved] = useState(false);
  const [health, setHealth] = useState<any>(null);
  const [sendingDiscord, setSendingDiscord] = useState(false);
  const [discordResult, setDiscordResult] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setPollingInterval(localStorage.getItem("yohanix_poll_interval") || "15");
      setAnimationsEnabled(localStorage.getItem("yohanix_animations") !== "false");
      setCompactView(localStorage.getItem("yohanix_compact") === "true");
    }
    api.health().then(setHealth).catch(() => {});
  }, []);

  function handleSave() {
    if (typeof window !== "undefined") {
      localStorage.setItem("yohanix_poll_interval", pollingInterval);
      localStorage.setItem("yohanix_animations", String(animationsEnabled));
      localStorage.setItem("yohanix_compact", String(compactView));
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  function handleExportData() {
    Promise.all([api.portfolio(), api.watchlist()]).then(([port, wl]) => {
      const data = { portfolio: port, watchlist: wl, exportedAt: new Date().toISOString() };
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `yohanix-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
    });
  }

  function handleSendDiscordTrades() {
    setSendingDiscord(true);
    setDiscordResult(null);
    api.sendDiscordTrades()
      .then((res) => {
        setDiscordResult(`✓ Successfully pushed ${res.count} ordered trades (Buy → Caution) to Discord!`);
      })
      .catch((err) => {
        setDiscordResult(`✕ Failed: ${err.message || "Webhook error or URL not configured"}`);
      })
      .finally(() => setSendingDiscord(false));
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-fade-in pb-12">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">UI Preferences & Settings</h1>
        <p className="text-sm text-slate-400 mt-1">Customize dashboard appearance, refresh rates, and webhook controls.</p>
      </div>

      {saved && (
        <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
          ✓ UI preferences saved successfully.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-lg">Discord Webhook Action Plan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-400">
              Push the complete ordered list of trades (sorted from best BUY down to CAUTION / SELL) instantly to your Discord webhook.
            </p>
            <div className="flex items-center gap-4">
              <Button
                onClick={handleSendDiscordTrades}
                disabled={sendingDiscord}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium shadow-lg shadow-emerald-500/20"
              >
                {sendingDiscord ? "Sending to Discord..." : "🚀 Push Ordered Trade List to Discord"}
              </Button>
            </div>
            {discordResult && (
              <p className={`text-xs mt-2 font-medium ${discordResult.startsWith("✓") ? "text-green-400" : "text-red-400"}`}>
                {discordResult}
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-lg">Dashboard Refresh Rate</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-400">Choose how often live data and trades automatically poll from the backend.</p>
            <div className="flex gap-3">
              {["5", "15", "30", "60"].map((s) => (
                <button
                  key={s}
                  onClick={() => setPollingInterval(s)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    pollingInterval === s
                      ? "bg-blue-600 text-white shadow-lg shadow-blue-500/25"
                      : "bg-slate-800/60 text-slate-300 hover:bg-slate-700/60"
                  }`}
                >
                  {s} Seconds
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-lg">Visuals & Animations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-200">Glow & Hover Transitions</p>
                <p className="text-xs text-slate-400">Enable card hover lift effects and pulse glowing borders.</p>
              </div>
              <input
                type="checkbox"
                checked={animationsEnabled}
                onChange={(e) => setAnimationsEnabled(e.target.checked)}
                className="w-4 h-4 accent-blue-500 rounded cursor-pointer"
              />
            </div>
            <div className="flex items-center justify-between pt-3 border-t border-slate-800/50">
              <div>
                <p className="text-sm font-medium text-slate-200">Compact Table Density</p>
                <p className="text-xs text-slate-400">Reduce table row padding for high-density monitoring.</p>
              </div>
              <input
                type="checkbox"
                checked={compactView}
                onChange={(e) => setCompactView(e.target.checked)}
                className="w-4 h-4 accent-blue-500 rounded cursor-pointer"
              />
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-lg">Data & Backup</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-400">Export a complete JSON backup of your current portfolio positions and watchlist.</p>
            <Button onClick={handleExportData} className="bg-slate-800 hover:bg-slate-700 text-slate-200">
              Export Backup JSON
            </Button>
          </CardContent>
        </Card>

        {health && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-lg">System Diagnostics</CardTitle>
            </CardHeader>
            <CardContent className="text-xs font-mono-data space-y-1.5 text-slate-400">
              <p>Status: <span className="text-green-400">{health.status}</span></p>
              <p>Python: {health.python_version?.split(" ")[0]}</p>
              <p>Cache Items: {health.cache_items}</p>
              <p>Outputs Directory: {health.outputs_dir_exists ? "Available" : "Missing"}</p>
              <p>Timestamp: {health.timestamp}</p>
            </CardContent>
          </Card>
        )}

        <div className="flex justify-end">
          <Button onClick={handleSave} className="bg-blue-600 hover:bg-blue-500 text-white font-medium px-6 py-2 shadow-lg shadow-blue-500/20">
            Save UI Preferences
          </Button>
        </div>
      </div>
    </div>
  );
}
