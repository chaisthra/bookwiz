import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Netflix-style dark theme base
        "nf-bg":       "#141414",
        "nf-surface":  "#1f1f1f",
        "nf-card":     "#2a2a2a",
        "nf-elevated": "#333333",
        // BookWiz brand palette
        parchment:    "#F5EFE0",
        "dusty-rose": "#C9A0A0",
        "deep-wine":  "#6B2737",
        "aged-gold":  "#C8A84B",
        "ink-black":  "#0a0a0a",
        "muted-sage": "#8A9E8A",
      },
      fontFamily: {
        serif: ["Georgia", "Cambria", "Times New Roman", "serif"],
        sans:  ["Inter", "system-ui", "sans-serif"],
      },
      keyframes: {
        "fade-up": {
          "0%":   { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.4s ease-out both",
        shimmer:   "shimmer 1.4s infinite",
      },
    },
  },
  plugins: [],
};

export default config;
