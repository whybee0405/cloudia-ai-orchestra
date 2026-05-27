/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cloudia: {
          50: '#f0f4ff',
          500: '#3b5bdb',
          600: '#2f4ac4',
          700: '#2340ab',
        },
      },
    },
  },
  plugins: [],
}
