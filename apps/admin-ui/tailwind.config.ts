import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        'nyaya-navy': '#1E3A5F',
        'nyaya-crimson': '#B91C1C',
      },
    },
  },
  plugins: [],
}
export default config
