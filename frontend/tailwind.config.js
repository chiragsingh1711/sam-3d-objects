/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#000000',
          surface: '#0a0a0a',
          elevated: '#141414',
          border: '#1f1f1f',
          text: {
            primary: '#ffffff',
            secondary: '#a0a0a0',
            tertiary: '#5a5a5a',
          }
        },
        accent: {
          primary: '#0a84ff',
          hover: '#0066cc',
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        'apple': '10px',
      }
    },
  },
  plugins: [],
}
