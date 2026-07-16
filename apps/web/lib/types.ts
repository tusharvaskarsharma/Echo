export type ConsentLevel = "private" | "family" | "legacy";

export type Memory = {
  id: string;
  session_id: string;
  content: string;
  emotion_tags: string[];
  people_mentioned: string[];
  topics: string[];
  time_period: string;
  confidence_score: number;
  consent_level: ConsentLevel;
  recorded_at: string;
  timestamp_seconds: number;
  x: number;
  y: number;
};

export type Source = {
  memory_id: string;
  session_id: string;
  excerpt: string;
  timestamp_seconds: number;
};

export type Profile = {
  id: string;
  name: string;
  age: number;
  voice: string;
  bio: string;
  session_count: number;
  memory_count: number;
};

