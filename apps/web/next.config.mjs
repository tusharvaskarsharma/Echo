import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// The app lives in apps/web while shared configuration is stored at the repo
// root. Load values the Next server needs before it starts. Provider keys stay
// server-only because they are never included in `nextConfig.env`.
const rootEnvFile = resolve(dirname(fileURLToPath(import.meta.url)), "../../.env");
try {
  for (const line of readFileSync(rootEnvFile, "utf8").split(/\r?\n/)) {
    const entry = line.match(/^(NEXT_PUBLIC_(?:SUPABASE_(?:URL|ANON_KEY)|API_BASE_URL))=(.*)$/);
    if (entry && !process.env[entry[1]]) process.env[entry[1]] = entry[2].trim().replace(/^("|')|("|')$/g, "");
  }
} catch {}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
