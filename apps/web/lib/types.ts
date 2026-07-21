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

export type GroupMember = {
  user_id: string;
  username: string | null;
  display_name: string;
  role: "owner" | "member";
  joined_at: string;
  is_current_user?: boolean;
};

export type FamilyGroup = {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  owner_name: string;
  owner_username: string | null;
  role: "owner" | "member";
  member_count: number;
  share_memories: boolean;
  created_at: string;
  members: GroupMember[];
};

export type SharedUser = {
  owner_id: string;
  subject_id: string | null;
  username: string | null;
  display_name: string;
};
