/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0A0E1A",
        panel: "#111827",
        border: "#1E2D50",
        primary: "#E8EDF8",
        secondary: "#8A99BB",
        success: "#10B981",
        alert: "#EF4444",
        phantom: "#F59E0B",
        accent: "#3B82F6",
      },
    },
  },
  plugins: [],
}
