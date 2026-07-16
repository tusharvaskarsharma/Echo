import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#F8F6F2",
        primary: "#A77464",
        secondary: "#D8C6B8",
        accent: "#E8DDD4",
        text: "#2F2A28",
        success: "#8FAE8B",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)"],
        serif: ["var(--font-instrument-serif)"],
      },
      boxShadow: {
        clay: "inset -8px -8px 16px rgba(0, 0, 0, 0.1), inset 8px 8px 16px rgba(255, 255, 255, 0.7), 8px 8px 24px rgba(0, 0, 0, 0.05)",
        "clay-sm": "inset -4px -4px 8px rgba(0, 0, 0, 0.1), inset 4px 4px 8px rgba(255, 255, 255, 0.7), 4px 4px 12px rgba(0, 0, 0, 0.05)",
        "clay-active": "inset 8px 8px 16px rgba(0, 0, 0, 0.1), inset -8px -8px 16px rgba(255, 255, 255, 0.7)",
      },
      borderRadius: {
        "clay": "24px",
        "clay-lg": "28px",
        "clay-full": "9999px",
      }
    },
  },
  plugins: [],
};

export default config;
