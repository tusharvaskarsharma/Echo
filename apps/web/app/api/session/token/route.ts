import { NextResponse } from 'next/server';

export async function POST() {
  // In demo mode, return a mock token
  // In production, this would proxy to the FastAPI backend
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  
  if (apiBase) {
    try {
      const response = await fetch(`${apiBase}/api/session/token`, {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer demo-token',
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch {
      // Fall through to demo response
    }
  }
  
  // Demo fallback
  return NextResponse.json({
    client_secret: 'demo_token_12345',
    expires_at: 1999999999
  });
}