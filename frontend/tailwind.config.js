/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        panel: '#0f172a',
        'panel-border': '#1e293b',
      },
    },
  },
  plugins: [],
}
