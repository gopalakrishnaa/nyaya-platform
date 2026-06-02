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
        'prajna-crimson': '#B91C1C',
        'prajna-saffron': '#F59E0B',
        'prajna-green': '#059669',
        'prajna-navy': '#1E3A5F',
      },
    },
  },
  plugins: [],
}
export default config
