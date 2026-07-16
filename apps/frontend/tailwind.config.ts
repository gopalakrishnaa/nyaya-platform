import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'prajna-crimson': '#7A1330',
        'prajna-saffron': '#C08A2E',
        'prajna-green': '#0F6B4F',
        'prajna-navy': '#14213D',
        'prajna-ink': '#0B1220',
        'prajna-paper': '#FAF7F1',
      },
      fontFamily: {
        serif: ['var(--font-prajna-serif)', 'Georgia', 'serif'],
        sans: ['var(--font-prajna-sans)', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
export default config
