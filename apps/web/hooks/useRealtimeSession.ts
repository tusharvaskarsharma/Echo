"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { API_BASE } from "../lib/api";

export function useRealtimeSession() {
  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Initialize audio element
  useEffect(() => {
    if (typeof window !== "undefined") {
      audioRef.current = document.createElement("audio");
      audioRef.current.autoplay = true;
    }
    return () => {
      if (audioRef.current) {
        audioRef.current.srcObject = null;
      }
    };
  }, []);

  const connect = useCallback(async () => {
    setError(null);
    try {
      // 1. Get ephemeral token from our FastAPI backend
      // Assuming the user is logged in and we pass their auth token if needed.
      // For now, simple fetch (ensure your auth token is attached in a real scenario).
      const tokenResponse = await fetch(`${API_BASE}/session/token`, {
        method: "POST",
      });
      if (!tokenResponse.ok) {
        throw new Error("Failed to get realtime token from server");
      }
      const data = await tokenResponse.json();
      const ephemeralKey = data.client_secret;

      // 2. Set up WebRTC
      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      // Set up remote audio playback
      pc.ontrack = (e) => {
        if (audioRef.current) {
          audioRef.current.srcObject = e.streams[0];
        }
      };

      // Get local microphone
      const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
      pc.addTrack(ms.getTracks()[0]);

      // Create DataChannel for events
      const dc = pc.createDataChannel("oai-events");
      dcRef.current = dc;

      dc.addEventListener("open", () => {
        setIsConnected(true);
      });

      dc.addEventListener("message", (e) => {
        try {
          const event = JSON.parse(e.data);
          setMessages((prev) => [...prev, event]);
          
          if (event.type === "response.audio_transcript.delta") {
            setTranscript((prev) => prev + event.delta);
          }
          if (event.type === "input_audio_buffer.speech_started") {
            setIsSpeaking(true);
            // Optionally clear transcript on new speech
            setTranscript(""); 
          }
          if (event.type === "input_audio_buffer.speech_stopped") {
            setIsSpeaking(false);
          }
        } catch (err) {
          console.error("Failed to parse event", err);
        }
      });

      // 3. Create offer and send to OpenAI
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const baseUrl = "https://api.openai.com/v1/realtime";
      const model = "gpt-4o-realtime-preview-2024-12-17";
      
      const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${ephemeralKey}`,
          "Content-Type": "application/sdp",
        },
      });

      if (!sdpResponse.ok) {
        throw new Error("Failed to connect to OpenAI Realtime");
      }

      const answer = {
        type: "answer" as RTCSdpType,
        sdp: await sdpResponse.text(),
      };
      await pc.setRemoteDescription(answer);

    } catch (err: any) {
      console.error(err);
      setError(err.message || "Connection failed");
      setIsConnected(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (dcRef.current) {
      dcRef.current.close();
    }
    if (pcRef.current) {
      pcRef.current.close();
    }
    setIsConnected(false);
    setIsSpeaking(false);
  }, []);

  return {
    connect,
    disconnect,
    isConnected,
    isSpeaking,
    transcript,
    messages,
    error,
  };
}