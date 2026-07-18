"use client";

import { motion } from "framer-motion";

interface AudioOrbProps {
  state: "disconnected" | "idle" | "listening" | "speaking";
  compact?: boolean;
  amplitude?: number;
}

export const AudioOrb = ({ state, compact = false, amplitude = 0 }: AudioOrbProps) => {
  const getVariants = (): any => {
    switch (state) {
      case "listening":
        return {
          scale: 1 + Math.min(0.18, amplitude * 0.45),
          boxShadow: [
            "inset -8px -8px 16px rgba(0,0,0,0.1), inset 8px 8px 16px rgba(255,255,255,0.7), 0px 0px 40px rgba(168, 85, 247, 0.4)",
            "inset -8px -8px 16px rgba(0,0,0,0.1), inset 8px 8px 16px rgba(255,255,255,0.7), 0px 0px 60px rgba(168, 85, 247, 0.6)",
            "inset -8px -8px 16px rgba(0,0,0,0.1), inset 8px 8px 16px rgba(255,255,255,0.7), 0px 0px 40px rgba(168, 85, 247, 0.4)",
          ],
          backgroundColor: "#F8F6F2",
          transition: { repeat: Infinity, duration: 1.5, ease: "easeInOut" }
        };
      case "speaking":
        return {
          scale: 1 + Math.min(0.22, amplitude * 0.5),
          boxShadow: [
            "inset -8px -8px 16px rgba(0,0,0,0.1), inset 8px 8px 16px rgba(255,255,255,0.7), 0px 0px 50px rgba(232, 221, 212, 0.8)",
            "inset -8px -8px 16px rgba(0,0,0,0.1), inset 8px 8px 16px rgba(255,255,255,0.7), 0px 0px 80px rgba(216, 198, 184, 1)",
            "inset -8px -8px 16px rgba(0,0,0,0.1), inset 8px 8px 16px rgba(255,255,255,0.7), 0px 0px 50px rgba(232, 221, 212, 0.8)",
          ],
          backgroundColor: "#D8C6B8",
          transition: { repeat: Infinity, duration: 1.2, ease: "easeInOut" }
        };
      case "idle":
        return {
          scale: [1, 1.02, 1],
          boxShadow: "inset -8px -8px 16px rgba(0,0,0,0.1), inset 8px 8px 16px rgba(255,255,255,0.7), 8px 8px 24px rgba(0,0,0,0.05)",
          backgroundColor: "#F8F6F2",
          transition: { repeat: Infinity, duration: 3, ease: "easeInOut" }
        };
      case "disconnected":
      default:
        return {
          scale: 1,
          boxShadow: "inset -4px -4px 8px rgba(0,0,0,0.05), inset 4px 4px 8px rgba(255,255,255,0.4)",
          backgroundColor: "#E5E5E5",
        };
    }
  };

  return (
    <div className={`flex items-center justify-center ${compact ? "h-40 w-40 sm:h-48 sm:w-48" : "h-64 w-64 md:h-80 md:w-80"}`}>
      <motion.div
        animate={getVariants()}
        className={`${compact ? "h-32 w-32 sm:h-40 sm:w-40" : "h-48 w-48 md:h-64 md:w-64"} rounded-full border border-white/40`}
      />
    </div>
  );
};
