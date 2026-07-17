"use client";

import { useState } from "react";
import { api } from "../lib/api";

export function SessionSimulator() {
  const [stage, setStage] = useState<"ready" | "recording" | "processing" | "done">("ready");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [flash, setFlash] = useState("");
  const begin = async () => {
    try {
      const session = await api.createSession();
      setSessionId(session.id);
      setStage("recording");
      setTimeout(() => setFlash("A new memory was captured: You were brave enough to begin."), 1600);
    } catch {
      setFlash("We could not start the session. Please try again.");
    }
  };
  const finish = async () => { if (!sessionId) return; await api.createDraft(sessionId, { content: "I told my grandchildren that mistakes are proof they were brave enough to begin.", emotion: "encouragement", topic: "values", people: ["grandchildren"] }); await api.finishSession(sessionId); setStage("processing"); setTimeout(() => setStage("done"), 2200); };
  return <section className="session-screen"><p className="eyebrow">A quiet space to remember</p><div className={`audio-orb ${stage}`}><span /></div><h1>{stage === "ready" ? "Whenever you are ready" : stage === "recording" ? "I&apos;m listening" : stage === "processing" ? "Holding your stories with care" : "Your memories are ready to review"}</h1><p className="session-copy">{stage === "ready" ? "Echo will ask warm questions and preserve only the stories you choose to share." : stage === "recording" ? "Take your time. Pauses are welcome." : stage === "processing" ? "Demo mode is organizing your session. In live mode this securely transcribes and extracts memories." : "A new draft memory was added to your constellation."}</p>{flash && stage === "recording" && <div className="memory-flash">{flash}</div>}<div className="session-actions">{stage === "ready" && <button onClick={begin}>Begin session</button>}{stage === "recording" && <><button className="secondary">Pause</button><button onClick={finish}>End session</button></>}{stage === "done" && <a className="button-link" href="/subject/dashboard">Review memories</a>}</div></section>;
}
