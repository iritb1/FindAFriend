import typography from "@tailwindcss/typography";

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      animation: {
        float: "float 7s ease-in-out infinite",
        blink: "blink 1.2s infinite ease-in-out",
      },
      keyframes: {
        float: {
          "0%, 100%": {
            transform: "translateY(0) scale(1)",
          },
          "50%": {
            transform: "translateY(-16px) scale(1.04)",
          },
        },
        blink: {
          "0%, 80%, 100%": {
            opacity: "0.3",
            transform: "translateY(0)",
          },
          "40%": {
            opacity: "1",
            transform: "translateY(-4px)",
          },
        },
      },
    },
  },
  plugins: [typography],
};