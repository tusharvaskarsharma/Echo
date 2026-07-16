"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface TranscriptStreamProps {
  transcript: string;
}

export const TranscriptStream = ({ transcript }: TranscriptStreamProps) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [transcript]);

  return (
    <div 
      ref={containerRef}
      className="w-full max-w-2xl mx-auto h-32 md:h-48 overflow-y-auto px-6 py-4 flex flex-col justify-end no-scrollbar"
    >
      <AnimatePresence mode="wait">
        <motion.p
          key={transcript ? transcript.substring(0,20) : "empty"} // Key change forces animation
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          className="text-2xl md:text-4xl text-text/80 text-center font-serif leading-relaxed"
        >
          {transcript || "..."}
        </motion.p>
      </AnimatePresence>
    </div>
  );
};