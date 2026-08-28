"use client";

import { ArrowUp, Mic, MicOff, Sparkles } from "lucide-react";
import { useState } from "react";

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

function classify(command: string) {
  const text = command.toLowerCase();
  if (/schedule|publish|post now|send live/.test(text)) return { label: "Scheduling plan", gate: "Human approval required", route: "Calendar" };
  if (/ugc|video ad|unboxing|creator ad|testimonial/.test(text)) return { label: "UGC creation", gate: "Draft only — safe to generate", route: "Create UGC" };
  return { label: "Campaign plan", gate: "Draft only — safe to generate", route: "Campaigns" };
}

export function AgentCommand() {
  const [command, setCommand] = useState("Create a 7-day launch campaign with two UGC ads for our summer offer");
  const [result, setResult] = useState<ReturnType<typeof classify> | null>(null);
  const [listening, setListening] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(true);

  function run() {
    if (!command.trim()) return;
    setResult(classify(command));
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
      setResult(classify(transcript));
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
      <button type="button" onClick={listen} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/10 hover:bg-white/15" aria-label="Speak command">{listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}</button>
      <button type="button" onClick={run} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white text-black hover:bg-[#b9ff66]" aria-label="Run command"><ArrowUp className="h-4 w-4" /></button>
    </div>
    {!voiceAvailable && <p className="mt-2 text-[11px] text-[#ffbf69]">Voice capture is not supported by this browser. Text commands still work.</p>}
    {result && <div className="mt-4 grid gap-2 sm:grid-cols-3">
      <div className="rounded-xl bg-white/[0.06] p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-white/35">Intent</p><p className="mt-1 text-sm">{result.label}</p></div>
      <div className="rounded-xl bg-white/[0.06] p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-white/35">Gate</p><p className="mt-1 text-sm">{result.gate}</p></div>
      <div className="rounded-xl bg-white/[0.06] p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-white/35">Next</p><p className="mt-1 text-sm">{result.route}</p></div>
    </div>}
  </div>;
}
