"use client";

import { useEffect, useState } from "react";
import { Check, Clock3, LoaderCircle, Mail, X } from "lucide-react";

import { AppNav } from "../../components/AppNav";
import { api } from "../../lib/api";
import type { GroupInvitation } from "../../lib/types";

export default function InvitationsPage() {
  const [invitations, setInvitations] = useState<GroupInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  const load = async () => {
    setLoading(true);
    try { setInvitations(await api.invitations()); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to load invitations."); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const respond = async (invitation: GroupInvitation, accept: boolean) => {
    setWorking(invitation.id); setMessage("");
    try {
      const result = accept ? await api.acceptInvitation(invitation.id) : await api.declineInvitation(invitation.id);
      setInvitations((current) => current.filter((item) => item.id !== invitation.id));
      setMessage(result.message || (accept ? "Invitation accepted. You can now access this Emmy." : "Invitation declined."));
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to update invitation."); }
    finally { setWorking(null); }
  };

  return <><AppNav /><main className="min-h-[calc(100vh-5rem)] bg-[radial-gradient(circle_at_12%_0%,#f1e4da_0,transparent_28%),#f8f6f2] px-4 py-8 sm:px-8"><div className="mx-auto max-w-3xl"><header className="mb-8"><p className="text-xs font-semibold uppercase tracking-[.2em] text-primary">Private notifications</p><h1 className="mt-2 font-serif text-5xl text-text">Family invitations</h1><p className="mt-3 text-sm leading-6 text-text/65">Accept only the groups you want to join. Until you accept, you have no access to their memories or Emmy.</p></header>{message && <p className="mb-5 rounded-2xl border border-primary/15 bg-white px-4 py-3 text-sm text-text/75" role="status">{message}</p>}{loading ? <div className="flex justify-center py-20 text-text/55"><LoaderCircle className="animate-spin" /></div> : invitations.length === 0 ? <section className="rounded-[30px] border border-dashed border-primary/25 bg-white/65 px-6 py-16 text-center"><Mail className="mx-auto text-primary" size={30} /><h2 className="mt-4 font-serif text-3xl text-text">No pending invitations</h2><p className="mt-2 text-sm text-text/60">When someone invites you to a family group, it will appear here.</p></section> : <div className="space-y-4">{invitations.map((invitation) => <article key={invitation.id} className="rounded-[28px] border border-primary/12 bg-white/85 p-6 shadow-[0_12px_35px_rgba(96,60,43,.07)]"><div className="flex items-start gap-4"><span className="rounded-2xl bg-primary/10 p-3 text-primary"><Mail size={21} /></span><div className="min-w-0 flex-1"><p className="text-xs font-semibold uppercase tracking-[.16em] text-primary">Family Group Invitation</p><h2 className="mt-1 font-serif text-3xl text-text">{invitation.group_name}</h2><p className="mt-2 text-sm leading-6 text-text/65">{invitation.inviter_name} invited you to join. The group currently has {invitation.member_count ?? 0} accepted member{invitation.member_count === 1 ? "" : "s"}.</p><p className="mt-3 inline-flex items-center gap-1.5 text-xs text-text/50"><Clock3 size={14} /> Expires {new Date(invitation.expires_at).toLocaleString()}</p><div className="mt-5 flex flex-wrap gap-3"><button type="button" disabled={working === invitation.id} onClick={() => void respond(invitation, true)} className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{working === invitation.id ? <LoaderCircle className="animate-spin" size={16} /> : <Check size={16} />}Accept invitation</button><button type="button" disabled={working === invitation.id} onClick={() => void respond(invitation, false)} className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700 disabled:opacity-50"><X size={16} />Decline</button></div></div></div></article>)}</div>}</div></main></>;
}
