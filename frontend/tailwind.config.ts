import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        border: "#d8dee8",
        surface: "#f7f9fc",
        ink: "#172033",
        muted: "#62708a",
        accent: "#2563eb"
      }
    }
  },
  plugins: []
};

export default config;
