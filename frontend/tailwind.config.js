/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#032341", 800: "#0A3455", 700: "#12466E" },
        copper: { DEFAULT: "#C36B4E", 600: "#A85539" },
        risk: { low: "#2E9E6B", medium: "#E0A83C", high: "#D64545" },
        surface: "#F4F6F9",
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', '"IBM Plex Sans Arabic"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "monospace"],
      },
    },
  },
  plugins: [],
};
