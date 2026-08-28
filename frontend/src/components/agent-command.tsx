"use client";

import { ArrowUp, Loader2, Mic, MicOff, Sparkles } from "lucide-react";
import { useState } from "react";
import { runAgentCommand, type AgentCommandResult } from "@/lib/studio-api";

type RecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: { results: ArrayLike<{ 0: { transcript: string } }> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
};

type RecognitionCtor = new () => RecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: RecognitionCtor;
    webkitSpeechRecognition?: RecognitionCtor;
  }
}

const intentLabels: Record<AgentCommandResult["intent"], { label: string; route: string }> = {
  schedule_content: { label: "Scheduling plan", route: "Calendar" },
  create_ugc: { label: "UGC creation", route: "Create UGC" },
  create_campaign: { label: "Campaign plan", route: "Campaigns" },
  status: { label: "Workspace status", route: "Settings" },
};

function present(result: AgentCommandResult) {
  const display = intentLabels[result.intent] || intentLabels.create_campaign;
  return {
    label: display.label,
    gate: result.requires_approval ? "Human approval required" : "Draft only — safe to generate",
    route: display.route,
    simulated: Boolean(result.simulated),
  };
}

export function AgentCommand() {
  const [command, setCommand] = useState("Create a 7-day launch campaign with two UGC ads for our summer offer");
  const [result, setResult] = useState<ReturnType<typeof present> | null>(null);
  const [listening, setListening] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(text = command) {
    if (!text.trim()) return;
    setWorking(true);
    setError(null);
    try {
      const response = await runAgentCommand(text.trim());
      setResult(present(response));
    } catch (reason) {
      setResult(null);
      setError(reason instanceof Error ? reason.message : "Agent command failed.");
    } finally {
      setWorking(false);
    }
  }

  function listen() {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) {
      setVoiceAvailable(false);
      return;
    }
    const recognition = new Ctor();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setCommand(transcript);
      void run(transcript);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    setListening(true);
    recognition.start();
  }

  return <div className="rounded-[22px] bg-[#10110f] p-4 text-white shadow-[0_24px_60px_rgba(0,0,0,.16)] sm:p-5">
    <div className="flex items-center gap-2 text-xs text-white/55"><Sparkles className="h-4 w-4 text-[#b9ff66]" /> Agent command</div>
    <div className="mt-4 flex items-end gap-2 rounded-2xl bg-white/[0.07] p-2 ring-1 ring-white/10">
      <textarea value={command} onChange={(event) => setCommand(event.target.value)} rows={2} className="min-h-[52px] flex-1 resize-none bg-transparent px-3 py-2 text-sm leading-6 text-white outline-none placeholder:text-white/35" placeholder="Tell the studio what outcome you want…" aria-label="Agent command" />
      <button type="button" onClick={listen} disabled={working} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/10 hover:bg-white/15 disabled:opacity-40" aria-label="Speak command">{listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}</button>
      <button type="button" onClick={() => void run()} disabled={working || !command.trim()} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white text-black hover:bg-[#b9ff66] disabled:opacity-40" aria-label="Run command">{working ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}</button>
    </div>
    {!voiceAvailable && <p className="mt-2 text-[11px] text-[#ffbf69]">Voice capture is not supported by this browser. Text commands still work.</p>}
    {error && <p className="mt-2 text-[11px] text-[#ff8f8f]" role="alert">{error}</p>}
    {result && <div className="mt-4 grid gap-2 sm:grid-cols-3">
      <div className="rounded-xl bg-white/[0.06] p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-white/35">Intent</p><p className="mt-1 text-sm">{result.label}</p></div>
      <div className="rounded-xl bg-white/[0.06] p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-white/35">Gate</p><p className="mt-1 text-sm">{result.gate}</p></div>
      <div className="rounded-xl bg-white/[0.06] p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-white/35">Next</p><p className="mt-1 text-sm">{result.route}{result.simulated ? " · Simulation" : ""}</p></div>
    </div>}
  </div>;
}
