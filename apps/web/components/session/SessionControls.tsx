"use client";

import { useState } from "react";
import { Mic, MicOff, PhoneOff } from "lucide-react";

interface SessionControlsProps {
  isConnected: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
}

export const SessionControls = ({ isConnected, onConnect, onDisconnect }: SessionControlsProps) => {
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex items-center justify-center gap-6">
        {!isConnected ? (
          <button 
            onClick={onConnect}
            className="clay-button-primary px-8 py-4 text-xl flex items-center gap-3"
          >
            <Mic className="w-6 h-6" />
            Start Session
          </button>
        ) : (
          <>
            <button 
              className="clay-button p-5 text-primary"
            >
              <MicOff className="w-8 h-8" />
            </button>
            
            <button 
              onClick={() => setShowConfirm(true)}
              className="bg-red-400 text-white shadow-clay-sm rounded-clay p-5 transition-all duration-300 hover:brightness-110 active:shadow-clay-active outline-none"
            >
              <PhoneOff className="w-8 h-8" />
            </button>
          </>
        )}
      </div>

      {showConfirm && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="clay-card p-8 max-w-md w-full mx-4 flex flex-col items-center text-center">
            <h3 className="text-4xl font-serif mb-4 text-text">End Session?</h3>
            <p className="text-xl text-text/70 mb-8">Are you sure you want to wrap up this conversation?</p>
            <div className="flex gap-4 w-full">
              <button 
                onClick={() => setShowConfirm(false)}
                className="clay-button flex-1 py-4 text-xl font-medium"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  onDisconnect();
                  setShowConfirm(false);
                }}
                className="bg-red-400 text-white shadow-clay-sm rounded-clay border border-white/20 transition-all duration-300 active:shadow-clay-active outline-none flex-1 py-4 text-xl font-medium"
              >
                End
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};