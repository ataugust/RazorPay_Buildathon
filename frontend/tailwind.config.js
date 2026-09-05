/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#080B10",
        card: "#10141B",
        border: "#202631",
        textPrimary: "#F5F7FA",
        textSecondary: "#9AA4B2",
        textMuted: "#667085",
        accent: "#6366F1",
        surface: "#0F131A",
        raised: "#121821",
        success: "#22C55E",
        warning: "#F59E0B",
        danger: "#EF4444",
      },
    },
  },
  plugins: [],
};
