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
        'nyaya-crimson': '#B91C1C',
        'nyaya-saffron': '#F59E0B',
        'nyaya-green': '#059669',
        'nyaya-navy': '#1E3A5F',
      },
    },
  },
  plugins: [],
}
export default config
