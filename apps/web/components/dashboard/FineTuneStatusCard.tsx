"use client";
import React from 'react';
import useSWR from 'swr';
import { BrainCircuit, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { API_BASE } from '../../lib/api';

const fetcher = (url: string) => fetch(url, {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
}).then(res => res.json());

export default function FineTuneStatusCard() {
  const { data, error } = useSWR(`${API_BASE}/finetune/status`, fetcher, { refreshInterval: 10000 });

  if (!data && !error) return (
    <div className="clay-card p-8 bg-primary/5 flex flex-col justify-center items-center h-full">
      <Loader2 className="w-8 h-8 animate-spin text-primary/50" />
    </div>
  );
  
  if (error) return (
    <div className="clay-card p-8 bg-primary/5 flex flex-col justify-center items-center h-full text-text/50">
      Failed to load AI status.
    </div>
  );

  const getStatusDisplay = () => {
    if (data.latest_job) {
      switch (data.latest_job.status) {
        case 'queued': return <span className="text-amber-600 flex items-center gap-2"><Loader2 className="w-5 h-5 animate-spin"/> Queued</span>;
        case 'uploading': return <span className="text-blue-500 flex items-center gap-2"><Loader2 className="w-5 h-5 animate-spin"/> Uploading Dataset...</span>;
        case 'running': return <span className="text-blue-600 flex items-center gap-2"><Loader2 className="w-5 h-5 animate-spin"/> Training...</span>;
        case 'completed': return <span className="text-success flex items-center gap-2"><CheckCircle className="w-5 h-5"/> Persona Active</span>;
        case 'failed': return <span className="text-red-500 flex items-center gap-2"><AlertCircle className="w-5 h-5"/> Training Failed</span>;
      }
    }
    
    if (data.enabled) {
      return <span className="text-text/70">Ready to train ({data.training_examples} memories)</span>;
    }
    
    return <span className="text-text/70">Collecting data ({data.training_examples}/150 memories)</span>;
  };

  return (
    <div className="clay-card p-8 bg-primary/5 flex flex-col justify-center h-full border border-primary/20">
      <h3 className="text-3xl font-serif mb-6 text-primary flex items-center gap-3">
        <BrainCircuit className="w-7 h-7" />
        AI Persona
      </h3>
      <div className="text-2xl font-medium">
        {getStatusDisplay()}
      </div>
      {data.model_id && (
        <p className="mt-4 text-sm text-text/50">Engine: {data.model_id}</p>
      )}
    </div>
  );
}
