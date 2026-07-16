"use client";
import React from 'react';
import { Memory } from '@/hooks/useMemoryGraph';
import ConsentSlider from './ConsentSlider';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';

interface Props {
  memory: Memory | null;
  onClose: () => void;
  onConsentChange: (id: string, consent: string) => void;
}

export default function MemoryDetails({ memory, onClose, onConsentChange }: Props) {
  return (
    <AnimatePresence>
      {memory && (
        <motion.div 
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="absolute top-4 right-4 bottom-4 w-full max-w-md bg-background/90 backdrop-blur-xl shadow-clay rounded-clay border border-white/50 p-6 flex flex-col z-20 overflow-y-auto"
        >
          <div className="flex justify-between items-center mb-6">
            <h2 className="font-serif text-2xl text-text">Memory Details</h2>
            <button onClick={onClose} className="p-2 hover:bg-secondary/20 rounded-full transition-colors">
              <X size={20} className="text-text/70" />
            </button>
          </div>
          
          <div className="space-y-6 flex-1">
            <div>
              <p className="text-text/60 text-sm font-medium mb-1">Content</p>
              <p className="text-text leading-relaxed bg-secondary/10 p-4 rounded-xl border border-secondary/20">{memory.content}</p>
            </div>
            
            <div>
              <p className="text-text/60 text-sm font-medium mb-2">Privacy Level</p>
              <ConsentSlider 
                consent={memory.consent_level} 
                onChange={(c) => onConsentChange(memory.id, c)} 
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-text/60 text-sm font-medium mb-1">Era</p>
                <div className="inline-block px-3 py-1 bg-secondary/30 text-text/80 text-sm rounded-full">
                  {memory.time_period || 'Unknown'}
                </div>
              </div>
              
              <div>
                <p className="text-text/60 text-sm font-medium mb-1">Confidence</p>
                <div className="inline-block px-3 py-1 bg-success/20 text-success text-sm rounded-full font-medium">
                  {Math.round(memory.confidence_score * 100)}%
                </div>
              </div>
            </div>
            
            {memory.topics && memory.topics.length > 0 && (
              <div>
                <p className="text-text/60 text-sm font-medium mb-2">Topics</p>
                <div className="flex flex-wrap gap-2">
                  {memory.topics.map(t => (
                    <span key={t} className="px-3 py-1 bg-primary/10 text-primary text-sm rounded-full border border-primary/20">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {memory.people_mentioned && memory.people_mentioned.length > 0 && (
              <div>
                <p className="text-text/60 text-sm font-medium mb-2">People Mentioned</p>
                <div className="flex flex-wrap gap-2">
                  {memory.people_mentioned.map(p => (
                    <span key={p} className="px-3 py-1 bg-accent text-text/80 text-sm rounded-full border border-secondary">
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
