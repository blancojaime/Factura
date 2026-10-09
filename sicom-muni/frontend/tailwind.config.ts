import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 50: "#eef4fb", 100: "#d6e4f5", 500: "#2e75b6", 600: "#245f94", 700: "#1f4e79", 900: "#14324e" },
      },
    },
  },
  plugins: [],
};
export default config;
