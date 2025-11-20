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
          surface: '#1c1c1e',
          elevated: '#2c2c2e',
          border: '#38383a',
          text: {
            primary: '#ffffff',
            secondary: '#98989d',
            tertiary: '#636366',
          }
        },
        accent: {
          primary: '#007aff',
          hover: '#0051d5',
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
