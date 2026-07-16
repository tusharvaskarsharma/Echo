"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Login() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    // Simulate magic link sending
    setTimeout(() => {
      setLoading(false);
      // For demo purposes, route directly to the dashboard
      router.push("/dashboard");
    }, 1500);
  };

  return (
    <div className="min-h-[100dvh] flex items-center justify-center p-6 relative overflow-hidden bg-background">
      {/* Decorative Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-primary/20 rounded-full blur-[100px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-secondary/40 rounded-full blur-[100px]" />

      <div className="clay-card p-12 w-full max-w-lg flex flex-col items-center relative z-10 bg-white/40 backdrop-blur-md">
        <h1 className="text-7xl font-serif text-primary mb-4 tracking-tight">Echo.</h1>
        <p className="text-2xl text-text/70 mb-12 text-center font-serif italic">Preserving your living legacy.</p>

        <form onSubmit={handleLogin} className="w-full flex flex-col gap-8">
          <div className="flex flex-col gap-3">
            <label htmlFor="email" className="text-xl font-medium ml-2 text-text/80">Email address</label>
            <input 
              id="email"
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="grandma@family.com"
              className="clay-card px-6 py-5 text-xl outline-none focus:ring-2 focus:ring-primary/50 bg-white/60 placeholder:text-text/40 transition-all duration-300"
              required
            />
          </div>
          
          <button 
            type="submit" 
            disabled={loading}
            className="clay-button-primary w-full py-5 text-2xl mt-4 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center"
          >
            {loading ? (
              <div className="w-8 h-8 border-4 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              "Sign In"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}