import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F7F5F0",
        ink: "#1C2320",
        surface: "#FFFFFF",
        line: "#E4E0D6",
        accent: {
          DEFAULT: "#0E6E5C",
          soft: "#E4F0EC",
        },
        steel: {
          DEFAULT: "#3B5BA5",
          soft: "#E8ECF7",
        },
        status: {
          uploaded: "#3B5BA5",
          queued: "#7C5CBF",
          processing: "#B4791E",
          completed: "#1F8A5F",
          failed: "#B3261E",
        },
      },
      fontFamily: {
        display: ["Georgia", "Cambria", "Times New Roman", "serif"],
      },
    },
  },
  plugins: [],
};

export default config;
