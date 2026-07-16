"use client";
import React, { useState, useRef } from 'react';
import { Play, Square, Loader2, Volume2 } from 'lucide-react';
import { API_BASE } from '../../lib/api';

interface Props {
  echoId: string;
}

export default function EchoResponse({ echoId }: Props) {
  const [question, setQuestion] = useState("");
  const [transcript, setTranscript] = useState("");
  const [sources, setSources] = useState<any[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);

  const playNextAudio = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      setIsSpeaking(false);
      return;
    }

    isPlayingRef.current = true;
    setIsSpeaking(true);
    const base64Audio = audioQueueRef.current.shift();
    
    if (base64Audio) {
      const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
      audio.onended = () => {
        playNextAudio();
      };
      audio.play().catch(e => {
        console.error("Audio playback failed", e);
        playNextAudio(); // skip to next
      });
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setTranscript("");
    setSources([]);
    setIsStreaming(true);
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    
    try {
      const formData = new FormData();
      formData.append("text", question);
      
      const response = await fetch(`${API_BASE}/echo/${echoId}/converse`, {
        method: "POST",
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let done = false;
      let buffer = "";
      
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        
        if (value) {
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || "";
          
          for (const part of parts) {
            if (part.startsWith('data: ')) {
              try {
                const data = JSON.parse(part.substring(6));
                
                if (data.type === "text") {
                  setTranscript(prev => prev + data.text);
                } else if (data.type === "audio") {
                  audioQueueRef.current.push(data.audio);
                  if (!isPlayingRef.current) {
                    playNextAudio();
                  }
                } else if (data.type === "sources") {
                  setSources(data.sources);
                }
              } catch (e) {
                console.error("Failed to parse SSE JSON chunk:", e);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsStreaming(false);
      setQuestion("");
    }
  };

  return (
    <div className="flex flex-col h-full bg-background p-6">
      <div className="flex-1 overflow-y-auto mb-4 p-6 bg-secondary/10 rounded-clay shadow-inner flex flex-col items-center relative">
        {!transcript && !isStreaming ? (
          <div className="text-text/50 font-serif text-2xl m-auto text-center max-w-md">
            Ask a question. Your loved one's synthesized persona will respond using their actual memories.
          </div>
        ) : (
          <div className="w-full max-w-3xl space-y-6">
            <div className="text-2xl text-text leading-relaxed font-serif bg-white/40 p-8 rounded-clay shadow-clay-sm border border-white/50 relative">
              {transcript}
              {isStreaming && <span className="inline-block w-3 h-6 ml-2 align-middle bg-primary animate-pulse rounded-full"/>}
              
              {isSpeaking && (
                <div className="absolute top-4 right-4 flex items-center gap-2 text-primary font-medium bg-primary/10 px-3 py-1 rounded-full text-sm">
                  <Volume2 className="w-4 h-4 animate-pulse" />
                  <span>Speaking</span>
                </div>
              )}
            </div>
            
            {sources.length > 0 && (
              <div className="mt-8 pt-6 border-t border-text/10">
                <p className="text-sm text-text/50 uppercase tracking-widest mb-3 font-semibold">Grounded Memories</p>
                <div className="space-y-3">
                  {sources.map((s, i) => (
                    <div key={i} className="text-md bg-white p-4 rounded-xl text-text/80 italic border border-white shadow-sm">
                      "{s.excerpt}"
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <form onSubmit={handleAsk} className="flex gap-4 max-w-3xl mx-auto w-full relative z-10">
        <input 
          type="text"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder="Ask a question about their life..."
          className="flex-1 px-8 py-5 rounded-full bg-white shadow-clay outline-none text-xl text-text focus:ring-2 ring-primary/20 transition-all border border-transparent focus:border-primary/20"
          disabled={isStreaming}
        />
        <button 
          type="submit" 
          disabled={isStreaming || !question.trim()}
          className="bg-primary text-white p-5 rounded-full shadow-clay disabled:opacity-50 hover:scale-105 transition-transform flex items-center justify-center w-16 h-16"
        >
          {isStreaming ? <Loader2 className="animate-spin w-8 h-8" /> : <Play fill="currentColor" className="w-7 h-7 ml-1" />}
        </button>
      </form>
    </div>
  );
}
