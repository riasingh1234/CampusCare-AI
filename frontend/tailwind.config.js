/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
      colors: {
        navy: {
          50: '#F2F5FA', 100: '#E3E9F3', 200: '#C5D0E3', 300: '#98A9C7', 400: '#667DA3',
          500: '#455E86', 600: '#33486B', 700: '#243653', 800: '#162540', 900: '#0B1B33',
        },
        brand: {
          50: '#EEF4FF', 100: '#DCE8FF', 200: '#B9D1FF', 300: '#8AB1FF', 400: '#5589F5',
          500: '#2F6BE8', 600: '#1D54CC', 700: '#1A44A5', 800: '#183A82', 900: '#152F66',
        },
      },
      boxShadow: {
        card: '0 0 0 1px rgba(11,27,51,0.06)',
        pop: '0 20px 40px -12px rgba(11,27,51,0.25)',
      },
    },
  },
  plugins: [],
};
