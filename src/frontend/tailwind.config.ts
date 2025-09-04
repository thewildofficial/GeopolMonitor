import type { Config } from "tailwindcss"
import { fontFamily } from "tailwindcss/defaultTheme"

const config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        chart: {
          "1": "hsl(var(--chart-1))",
          "2": "hsl(var(--chart-2))",
          "3": "hsl(var(--chart-3))",
          "4": "hsl(var(--chart-4))",
          "5": "hsl(var(--chart-5))",
        },
        // Intelligence Agency Theme Colors
        intel: {
          bg: "hsl(var(--intel-bg))",
          surface: "hsl(var(--intel-surface))",
          "surface-elevated": "hsl(var(--intel-surface-elevated))",
          border: "hsl(var(--intel-border))",
          "border-glow": "hsl(var(--intel-border-glow))",
          "text-primary": "hsl(var(--intel-text-primary))",
          "text-secondary": "hsl(var(--intel-text-secondary))",
          "text-muted": "hsl(var(--intel-text-muted))",
          accent: "hsl(var(--intel-accent))",
          "accent-hover": "hsl(var(--intel-accent-hover))",
          warning: "hsl(var(--intel-warning))",
          danger: "hsl(var(--intel-danger))",
          success: "hsl(var(--intel-success))",
          info: "hsl(var(--intel-info))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Inter", "var(--font-sans)", ...fontFamily.sans],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "Liberation Mono", "Courier New", "monospace"],
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "intel-pulse": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        "intel-scan": {
          "0%": { left: "-100%" },
          "100%": { left: "100%" },
        },
        "intel-glow": {
          "0%, 100%": { boxShadow: "0 0 5px hsl(var(--intel-accent) / 0.3)" },
          "50%": { boxShadow: "0 0 20px hsl(var(--intel-accent) / 0.6)" },
        },
        "intel-flicker": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.8" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "intel-pulse": "intel-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "intel-scan": "intel-scan 3s linear infinite",
        "intel-glow": "intel-glow 2s ease-in-out infinite",
        "intel-flicker": "intel-flicker 0.15s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config

export default config