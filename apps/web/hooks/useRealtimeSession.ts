"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const GEMINI_LIVE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained";
const INPUT_SAMPLE_RATE = 16_000;
const OUTPUT_SAMPLE_RATE = 24_000;

function bytesToBase64(bytes: Uint8Array) {
  let binary = "";
  for (let index = 0; index < bytes.length; index += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000));
  }
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
  const length = Math.max(1, Math.round(samples.length / ratio));
  const pcm = new Int16Array(length);
  for (let outputIndex = 0; outputIndex < length; outputIndex += 1) {
    const sourceIndex = outputIndex * ratio;
    const lower = Math.floor(sourceIndex);
    const upper = Math.min(lower + 1, samples.length - 1);
    const fraction = sourceIndex - lower;
    const sample = samples[lower] * (1 - fraction) + samples[upper] * fraction;
    pcm[outputIndex] = Math.max(-1, Math.min(1, sample)) * 0x7fff;
  }
  return new Uint8Array(pcm.buffer);
}

export function useRealtimeSession() {
  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const outputContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const mutedGainRef = useRef<GainNode | null>(null);
  const nextAudioTimeRef = useRef(0);
  const connectedRef = useRef(false);

  const cleanup = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    mutedGainRef.current?.disconnect();
    processorRef.current = null;
    sourceRef.current = null;
    mutedGainRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    void inputContextRef.current?.close();
    void outputContextRef.current?.close();
    inputContextRef.current = null;
    outputContextRef.current = null;
    nextAudioTimeRef.current = 0;
    connectedRef.current = false;
    setIsConnected(false);
    setIsSpeaking(false);
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const playGeminiAudio = useCallback(async (base64: string) => {
    let context = outputContextRef.current;
    if (!context) {
      context = new AudioContext();
      outputContextRef.current = context;
    }
    await context.resume();
    const pcm = base64ToInt16(base64);
    const audioBuffer = context.createBuffer(1, pcm.length, OUTPUT_SAMPLE_RATE);
    const channel = audioBuffer.getChannelData(0);
    for (let index = 0; index < pcm.length; index += 1) channel[index] = pcm[index] / 0x8000;
    const source = context.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(context.destination);
    const startAt = Math.max(context.currentTime + 0.03, nextAudioTimeRef.current);
    source.start(startAt);
    nextAudioTimeRef.current = startAt + audioBuffer.duration;
  }, []);

  const connect = useCallback(async () => {
    cleanup();
    setError(null);
    try {
      console.info("[Gemini Live] Requesting microphone permission");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      streamRef.current = stream;

      // Request only after permission: a Gemini ephemeral token has one minute
      // to begin its one allowed session.
      const tokenResponse = await fetch("/api/session/token", { method: "POST" });
      const tokenPayload = await tokenResponse.json().catch(() => null);
      if (!tokenResponse.ok) throw new Error(tokenPayload?.error || tokenPayload?.detail || "Unable to start Gemini Live.");
      if (!tokenPayload?.access_token || !tokenPayload?.model) throw new Error("The server did not return a Gemini Live token and model.");

      const url = `${GEMINI_LIVE_URL}?access_token=${encodeURIComponent(tokenPayload.access_token)}`;
      const socket = new WebSocket(url);
      socketRef.current = socket;
      socket.addEventListener("open", () => {
        console.info("[Gemini Live] WebSocket connected; sending setup", { model: tokenPayload.model });
        socket.send(JSON.stringify({
          setup: {
            model: `models/${tokenPayload.model}`,
            responseModalities: ["AUDIO"],
            inputAudioTranscription: {},
            outputAudioTranscription: {},
            systemInstruction: { parts: [{ text: "You are Echo, a thoughtful interviewer helping capture the user's life story. Ask empathetic, concise follow-up questions." }] },
          },
        }));
      });
      socket.addEventListener("error", () => setError("Gemini Live WebSocket connection failed."));
      socket.addEventListener("close", () => {
        console.info("[Gemini Live] WebSocket closed");
        connectedRef.current = false;
        setIsConnected(false);
        setIsSpeaking(false);
      });
      socket.addEventListener("message", async (event) => {
        const message = JSON.parse(event.data);
        setMessages((previous) => [...previous, message]);
        if (message.error) {
          setError(message.error.message || "Gemini Live returned an error.");
          return;
        }
        if (message.setupComplete) {
          console.info("[Gemini Live] Setup complete; streaming microphone audio");
          connectedRef.current = true;
          setIsConnected(true);
          return;
        }
        const content = message.serverContent;
        if (!content) return;
        if (content.inputTranscription?.text) setTranscript((previous) => `${previous}${previous ? "\n" : ""}${content.inputTranscription.text}`);
        if (content.outputTranscription?.text) setTranscript((previous) => `${previous}${previous ? "\nEcho: " : "Echo: "}${content.outputTranscription.text}`);
        if (content.modelTurn?.parts) {
          for (const part of content.modelTurn.parts) {
            if (part.inlineData?.data) await playGeminiAudio(part.inlineData.data);
          }
        }
        if (content.turnComplete) setIsSpeaking(false);
      });

      const inputContext = new AudioContext();
      inputContextRef.current = inputContext;
      await inputContext.resume();
      const source = inputContext.createMediaStreamSource(stream);
      const processor = inputContext.createScriptProcessor(4096, 1, 1);
      const mutedGain = inputContext.createGain();
      mutedGain.gain.value = 0;
      sourceRef.current = source;
      processorRef.current = processor;
      mutedGainRef.current = mutedGain;
      processor.onaudioprocess = (audioEvent) => {
        if (socket.readyState !== WebSocket.OPEN || !connectedRef.current) return;
        setIsSpeaking(true);
        const pcm = resampleToPcm16(audioEvent.inputBuffer.getChannelData(0), inputContext.sampleRate);
        socket.send(JSON.stringify({ realtimeInput: { audio: { data: bytesToBase64(pcm), mimeType: "audio/pcm;rate=16000" } } }));
      };
      source.connect(processor);
      processor.connect(mutedGain);
      mutedGain.connect(inputContext.destination);
    } catch (connectError: any) {
      console.error("[Gemini Live] Connection failed", connectError);
      cleanup();
      setError(connectError.message || "Gemini Live connection failed.");
    }
  }, [cleanup, playGeminiAudio]);

  const disconnect = useCallback(() => cleanup(), [cleanup]);

  const submitText = useCallback((text: string) => {
    const cleanText = text.trim();
    if (!cleanText) return;
    setTranscript((previous) => `${previous}${previous ? "\n" : ""}${cleanText}`);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ realtimeInput: { text: cleanText } }));
    }
  }, []);

  return { connect, disconnect, isConnected, isSpeaking, transcript, messages, error, submitText };
}
