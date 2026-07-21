"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { MemoryFlashItem } from "@/components/session/MemoryFlash";

const GEMINI_LIVE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained";
const INPUT_SAMPLE_RATE = 16_000;
const OUTPUT_SAMPLE_RATE = 24_000;
const MAX_RECONNECT_ATTEMPTS = 3;

export type ConversationMessage = { id: string; speaker: "emmy" | "user"; text: string };
type LiveToken = { access_token: string; session_id: string; model: string; setup: Record<string, unknown>; expires_at: string };

function bytesToBase64(bytes: Uint8Array) {
  let binary = "";
  for (let index = 0; index < bytes.length; index += 0x8000) binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000));
  return btoa(binary);
}

function base64ToInt16(base64: string) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new Int16Array(bytes.buffer);
}

function resampleToPcm16(samples: Float32Array, sourceRate: number) {
  const ratio = sourceRate / INPUT_SAMPLE_RATE;
  const pcm = new Int16Array(Math.max(1, Math.round(samples.length / ratio)));
  for (let outputIndex = 0; outputIndex < pcm.length; outputIndex += 1) {
    const sourceIndex = outputIndex * ratio;
    const lower = Math.floor(sourceIndex);
    const upper = Math.min(lower + 1, samples.length - 1);
    const sample = samples[lower] * (1 - (sourceIndex - lower)) + samples[upper] * (sourceIndex - lower);
    pcm[outputIndex] = Math.max(-1, Math.min(1, sample)) * 0x7fff;
  }
  return new Uint8Array(pcm.buffer);
}

function analyserLevel(analyser: AnalyserNode | null) {
  if (!analyser) return 0;
  const samples = new Uint8Array(analyser.fftSize);
  analyser.getByteTimeDomainData(samples);
  const rms = Math.sqrt(samples.reduce((total, sample) => total + ((sample - 128) / 128) ** 2, 0) / samples.length);
  return Math.min(1, rms * 6);
}

export function useRealtimeSession() {
  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [activeSpeaker, setActiveSpeaker] = useState<"emmy" | "subject" | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [memoryFlashes, setMemoryFlashes] = useState<MemoryFlashItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const outputContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const mutedGainRef = useRef<GainNode | null>(null);
  const inputAnalyserRef = useRef<AnalyserNode | null>(null);
  const outputAnalyserRef = useRef<AnalyserNode | null>(null);
  const nextAudioTimeRef = useRef(0);
  const connectedRef = useRef(false);
  const manualDisconnectRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const amplitudeFrameRef = useRef<number | null>(null);
  const emmyUntilRef = useRef(0);
  const sessionIdRef = useRef<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);

  const addTranscriptMessage = useCallback((speaker: ConversationMessage["speaker"], text: string) => {
    const cleanText = text.trim();
    if (!cleanText) return;
    setMessages((previous) => {
      const last = previous.at(-1);
      if (last?.speaker === speaker) return [...previous.slice(0, -1), { ...last, text: `${last.text}${last.text.endsWith(" ") ? "" : " "}${cleanText}` }];
      return [...previous, { id: `${speaker}-${Date.now()}-${Math.random().toString(36).slice(2)}`, speaker, text: cleanText }];
    });
    setTranscript((previous) => `${previous}${previous ? "\n" : ""}${speaker === "emmy" ? "Emmy" : "You"}: ${cleanText}`);
  }, []);

  const showMemoryFlash = useCallback((summary: string, topics: string[]) => {
    const flash = { id: `memory-${Date.now()}-${Math.random().toString(36).slice(2)}`, summary, topics };
    setMemoryFlashes((previous) => [...previous, flash].slice(-3));
    window.setTimeout(() => setMemoryFlashes((previous) => previous.filter((item) => item.id !== flash.id)), 7000);
  }, []);

  const sampleAmplitude = useCallback(() => {
    const inputLevel = analyserLevel(inputAnalyserRef.current);
    const outputLevel = analyserLevel(outputAnalyserRef.current);
    const emmyActive = outputLevel > 0.025 || performance.now() < emmyUntilRef.current;
    const subjectActive = inputLevel > 0.035;
    const speaker = emmyActive ? "emmy" : subjectActive ? "subject" : null;
    setAudioLevel(Math.max(inputLevel, outputLevel));
    setActiveSpeaker(speaker);
    setIsSpeaking(Boolean(speaker));
    amplitudeFrameRef.current = requestAnimationFrame(sampleAmplitude);
  }, []);

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
    reconnectTimerRef.current = null;
    if (amplitudeFrameRef.current) cancelAnimationFrame(amplitudeFrameRef.current);
    amplitudeFrameRef.current = null;
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    mediaRecorderRef.current = null;
    recordingChunksRef.current = [];
    socketRef.current?.close(); socketRef.current = null;
    processorRef.current?.disconnect(); sourceRef.current?.disconnect(); mutedGainRef.current?.disconnect();
    inputAnalyserRef.current?.disconnect(); outputAnalyserRef.current?.disconnect();
    processorRef.current = null; sourceRef.current = null; mutedGainRef.current = null;
    inputAnalyserRef.current = null; outputAnalyserRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop()); streamRef.current = null;
    void inputContextRef.current?.close(); void outputContextRef.current?.close();
    inputContextRef.current = null; outputContextRef.current = null; nextAudioTimeRef.current = 0;
    connectedRef.current = false; setIsConnected(false); setIsSpeaking(false); setActiveSpeaker(null); setAudioLevel(0);
  }, []);

  useEffect(() => () => { manualDisconnectRef.current = true; cleanup(); }, [cleanup]);

  const requestToken = useCallback(async (existingSessionId?: string | null): Promise<LiveToken> => {
    const response = await fetch("/api/session/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(existingSessionId ? { session_id: existingSessionId } : {}),
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new Error(payload?.error || payload?.detail || "Unable to start Gemini Live.");
    if (!payload?.access_token || !payload?.session_id || !payload?.setup) throw new Error("The server did not return a complete Live session credential.");
    return payload as LiveToken;
  }, []);

  const openSocketRef = useRef<(token: LiveToken) => void>(() => undefined);
  const reconnect = useCallback(async () => {
    if (manualDisconnectRef.current || reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) return;
    reconnectAttemptsRef.current += 1;
    try {
      // A fresh Gemini credential is required for every WebSocket reconnect,
      // while the server-created session id remains stable for the recording.
      const token = await requestToken(sessionIdRef.current);
      sessionIdRef.current = token.session_id;
      setSessionId(token.session_id);
      openSocketRef.current(token);
    } catch (reconnectError) {
      console.error("[Gemini Live] Reconnect failed", reconnectError);
      if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) setError("Voice connection was lost. Please start the session again.");
      else reconnectTimerRef.current = window.setTimeout(() => { void reconnect(); }, 1000 * 2 ** reconnectAttemptsRef.current);
    }
  }, [requestToken]);

  const playGeminiAudio = useCallback(async (base64: string) => {
    let context = outputContextRef.current;
    if (!context) { context = new AudioContext(); outputContextRef.current = context; }
    await context.resume();
    if (!outputAnalyserRef.current) {
      outputAnalyserRef.current = context.createAnalyser();
      outputAnalyserRef.current.fftSize = 1024;
      outputAnalyserRef.current.connect(context.destination);
    }
    const pcm = base64ToInt16(base64);
    const audioBuffer = context.createBuffer(1, pcm.length, OUTPUT_SAMPLE_RATE);
    const channel = audioBuffer.getChannelData(0);
    for (let index = 0; index < pcm.length; index += 1) channel[index] = pcm[index] / 0x8000;
    const source = context.createBufferSource(); source.buffer = audioBuffer; source.connect(outputAnalyserRef.current);
    const startAt = Math.max(context.currentTime + 0.03, nextAudioTimeRef.current);
    source.start(startAt); nextAudioTimeRef.current = startAt + audioBuffer.duration;
    emmyUntilRef.current = performance.now() + Math.max(50, (nextAudioTimeRef.current - context.currentTime) * 1000);
  }, []);

  const handleToolCalls = useCallback((socket: WebSocket, message: any) => {
    const calls = message.toolCall?.functionCalls || [];
    if (!calls.length) return;
    const responses = calls.map((call: any) => {
      if (call.name === "tag_memory") {
        const summary = typeof call.args?.summary === "string" ? call.args.summary.slice(0, 280) : "A meaningful memory was marked for review.";
        const topics = Array.isArray(call.args?.topics) ? call.args.topics.filter((topic: unknown) => typeof topic === "string").slice(0, 3) : [];
        showMemoryFlash(summary, topics);
        return { id: call.id, name: call.name, response: { accepted: true } };
      }
      return { id: call.id, name: call.name, response: { accepted: false, reason: "Unknown Emmy tool" } };
    });
    if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ toolResponse: { functionResponses: responses } }));
  }, [showMemoryFlash]);

  const openSocket = useCallback((token: LiveToken) => {
    // Detach a replaced socket before closing it. Its `close` event must not
    // schedule a second reconnect after a successful handover.
    const previousSocket = socketRef.current;
    socketRef.current = null;
    previousSocket?.close();
    const socket = new WebSocket(`${GEMINI_LIVE_URL}?access_token=${encodeURIComponent(token.access_token)}`);
    socketRef.current = socket;
    socket.addEventListener("open", () => {
      console.info("[Gemini Live] WebSocket connected; sending constrained setup", { model: token.model, sessionId: token.session_id });
      socket.send(JSON.stringify({ setup: token.setup }));
    });
    socket.addEventListener("error", () => setError("Gemini Live WebSocket connection failed."));
    socket.addEventListener("close", () => {
      if (socketRef.current !== socket) return;
      connectedRef.current = false; setIsConnected(false); setActiveSpeaker(null); setIsSpeaking(false);
      if (!manualDisconnectRef.current && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = 1000 * 2 ** reconnectAttemptsRef.current;
        setError(`Voice connection interrupted. Reconnecting… (${reconnectAttemptsRef.current + 1}/${MAX_RECONNECT_ATTEMPTS})`);
        reconnectTimerRef.current = window.setTimeout(() => { void reconnect(); }, delay);
      }
    });
    socket.addEventListener("message", async (event) => {
      try {
        const raw = event.data instanceof Blob ? await event.data.text() : event.data instanceof ArrayBuffer ? new TextDecoder().decode(event.data) : String(event.data);
        const message = JSON.parse(raw);
        if (message.error) { setError(message.error.message || "Gemini Live returned an error."); return; }
        if (message.setupComplete) { connectedRef.current = true; reconnectAttemptsRef.current = 0; setIsConnected(true); setError(null); return; }
        handleToolCalls(socket, message);
        const content = message.serverContent; if (!content) return;
        if (content.inputTranscription?.text) addTranscriptMessage("user", content.inputTranscription.text);
        if (content.outputTranscription?.text) addTranscriptMessage("emmy", content.outputTranscription.text);
        for (const part of content.modelTurn?.parts || []) if (part.inlineData?.data) await playGeminiAudio(part.inlineData.data);
      } catch (messageError) {
        console.error("[Gemini Live] Unable to decode a server message", messageError);
        setError("Gemini Live returned an unreadable server message.");
      }
    });
  }, [addTranscriptMessage, handleToolCalls, playGeminiAudio, reconnect]);

  useEffect(() => { openSocketRef.current = openSocket; }, [openSocket]);

  const connect = useCallback(async (persistedSessionId?: string) => {
    manualDisconnectRef.current = true;
    cleanup();
    manualDisconnectRef.current = false;
    reconnectAttemptsRef.current = 0;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      streamRef.current = stream;
      if (typeof MediaRecorder !== "undefined") {
        try {
          const recorder = new MediaRecorder(stream);
          recordingChunksRef.current = [];
          recorder.addEventListener("dataavailable", (event) => {
            if (event.data.size) recordingChunksRef.current.push(event.data);
          });
          recorder.start(1_000);
          mediaRecorderRef.current = recorder;
        } catch (recordingError) {
          // Live audio still works if a browser supports Web Audio but cannot
          // encode a persisted recording. The UI can use transcript fallback.
          console.warn("[Gemini Live] Browser recording is unavailable", recordingError);
        }
      }
      const inputContext = new AudioContext(); inputContextRef.current = inputContext; await inputContext.resume();
      const source = inputContext.createMediaStreamSource(stream);
      const analyser = inputContext.createAnalyser(); analyser.fftSize = 1024;
      const processor = inputContext.createScriptProcessor(4096, 1, 1);
      const mutedGain = inputContext.createGain(); mutedGain.gain.value = 0;
      sourceRef.current = source; inputAnalyserRef.current = analyser; processorRef.current = processor; mutedGainRef.current = mutedGain;
      processor.onaudioprocess = (audioEvent) => {
        const socket = socketRef.current;
        if (!socket || socket.readyState !== WebSocket.OPEN || !connectedRef.current) return;
        const pcm = resampleToPcm16(audioEvent.inputBuffer.getChannelData(0), inputContext.sampleRate);
        // Gemini Live's equivalent of OpenAI input_audio_buffer.append.
        socket.send(JSON.stringify({ realtimeInput: { audio: { data: bytesToBase64(pcm), mimeType: "audio/pcm;rate=16000" } } }));
      };
      source.connect(analyser); analyser.connect(processor); processor.connect(mutedGain); mutedGain.connect(inputContext.destination);
      amplitudeFrameRef.current = requestAnimationFrame(sampleAmplitude);
      const token = await requestToken(persistedSessionId);
      sessionIdRef.current = token.session_id;
      setSessionId(token.session_id);
      openSocket(token);
    } catch (connectError: any) {
      console.error("[Gemini Live] Connection failed", connectError);
      manualDisconnectRef.current = true; cleanup();
      setError(connectError.message || "Gemini Live connection failed.");
    }
  }, [cleanup, openSocket, requestToken, sampleAmplitude]);

  const disconnect = useCallback(() => { manualDisconnectRef.current = true; cleanup(); }, [cleanup]);
  const finishRecording = useCallback((): Promise<Blob | null> => new Promise((resolve) => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) { resolve(null); return; }
    const complete = () => {
      mediaRecorderRef.current = null;
      const chunks = recordingChunksRef.current;
      recordingChunksRef.current = [];
      resolve(chunks.length ? new Blob(chunks, { type: recorder.mimeType || "audio/webm" }) : null);
    };
    if (recorder.state === "inactive") { complete(); return; }
    recorder.addEventListener("stop", complete, { once: true });
    recorder.stop();
  }), []);
  const submitText = useCallback((text: string) => {
    const cleanText = text.trim(); if (!cleanText) return;
    addTranscriptMessage("user", cleanText);
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ realtimeInput: { text: cleanText } }));
    else setError("Voice connection is not active. Start or reconnect the session to send a response.");
  }, [addTranscriptMessage]);

  return { connect, disconnect, finishRecording, isConnected, isSpeaking, activeSpeaker, audioLevel, sessionId, transcript, messages, memoryFlashes, error, submitText };
}
