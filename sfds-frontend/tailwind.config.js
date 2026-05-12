/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // SFDS Calm Color Palette
        sfds: {
          bg: {
            primary: '#faf9f7',
            secondary: '#f5f3f0',
            card: '#ffffff',
          },
          text: {
            primary: '#3d3d3d',
            secondary: '#6b6b6b',
            muted: '#9a9a9a',
          },
          accent: {
            teal: '#5a9a8f',
            'teal-light': '#e8f4f2',
            sage: '#8fa872',
            'sage-light': '#f0f5eb',
            warm: '#c4a77d',
            'warm-light': '#faf6f0',
          },
          border: '#e8e6e3',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'sans-serif'],
      },
      boxShadow: {
        'sfds': '0 2px 8px rgba(0, 0, 0, 0.04)',
        'sfds-hover': '0 4px 16px rgba(0, 0, 0, 0.06)',
      },
      borderRadius: {
        'sfds': '12px',
        'sfds-sm': '8px',
        'sfds-lg': '16px',
      },
    },
  },
  plugins: [],
};
