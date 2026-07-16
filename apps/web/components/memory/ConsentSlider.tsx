"use client";
import React from 'react';

interface Props {
  consent: 'private' | 'family' | 'legacy';
  onChange: (c: 'private' | 'family' | 'legacy') => void;
}

export default function ConsentSlider({ consent, onChange }: Props) {
  const levels = [
    { id: 'private', label: '🔒 Private' },
    { id: 'family', label: '👨‍👩‍👧 Family' },
    { id: 'legacy', label: '🌍 Legacy' }
  ];

  return (
    <div className="flex bg-secondary/20 p-1 rounded-full shadow-inner w-full">
      {levels.map(lvl => (
        <button
          key={lvl.id}
          onClick={() => onChange(lvl.id as any)}
          className={`flex-1 py-2 px-1 text-xs md:text-sm font-medium rounded-full transition-all duration-300 ${
            consent === lvl.id 
              ? 'bg-background shadow-clay text-primary' 
              : 'text-text/70 hover:text-text'
          }`}
        >
          {lvl.label}
        </button>
      ))}
    </div>
  );
}