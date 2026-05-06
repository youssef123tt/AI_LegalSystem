import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f6f6",
          100: "#e7e7e7",
          200: "#cfcfcf",
          300: "#b0b0b0",
          400: "#8a8a8a",
          500: "#6b6b6b",
          600: "#545454",
          700: "#3f3f3f",
          800: "#2a2a2a",
          900: "#151515"
        },
        paper: "#fbf7ef",
        accent: {
          50: "#fff6ed",
          100: "#ffe6d1",
          200: "#ffc99c",
          300: "#ffad66",
          400: "#ff8d2d",
          500: "#f26d0a",
          600: "#c85606",
          700: "#9e4307",
          800: "#6f320a",
          900: "#3c1e08"
        }
      },
      fontFamily: {
        display: ["\"Iowan Old Style\"", "Cambria", "Georgia", "serif"],
        body: ["\"Segoe UI\"", "Tahoma", "Arial", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"]
      },
      boxShadow: {
        card: "0 1px 0 rgba(0,0,0,0.06), 0 12px 30px rgba(0,0,0,0.10)"
      },
      borderRadius: {
        xl: "1rem"
      }
    }
  },
  plugins: []
} satisfies Config;

