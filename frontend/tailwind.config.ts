import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#07090c",
          900: "#0c1016",
          800: "#121821",
          700: "#1a2230",
          600: "#243044",
        },
        line: "#243044",
        gain: "#3dd68c",
        loss: "#f07178",
        warn: "#e6b450",
        mute: "#8b9bb4",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
