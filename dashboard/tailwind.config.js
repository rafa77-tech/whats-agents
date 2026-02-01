/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        revoluna: {
          50: '#FADCDE',
          100: '#F5B8BC',
          200: '#E85A63',
          300: '#D64550',
          400: '#C82D37',
          500: '#C82D37',
          600: '#A52530',
          700: '#7A1B22',
          800: '#5A1419',
          900: '#3A0D10',
        },
        gray: {
          50: '#F7F7F7',
          100: '#E2E8F0',
          200: '#CBD5E0',
          300: '#A0AEC0',
          400: '#718096',
          500: '#4A5568',
          600: '#2D3748',
          700: '#1A202C',
          800: '#171923',
          900: '#0D1117',
        },
        success: {
          DEFAULT: '#38A169',
          light: '#C6F6D5',
          dark: '#276749',
        },
        warning: {
          DEFAULT: '#D69E2E',
          light: '#FEFCBF',
          dark: '#975A16',
        },
        info: {
          DEFAULT: '#3182CE',
          light: '#BEE3F8',
          dark: '#2C5282',
        },
        gold: '#D4A853',
        teal: '#2D8C7A',
        chart: {
          1: 'hsl(var(--chart-1))',
          2: 'hsl(var(--chart-2))',
          3: 'hsl(var(--chart-3))',
          4: 'hsl(var(--chart-4))',
          5: 'hsl(var(--chart-5))',
        },
        state: {
          handoff: {
            DEFAULT: 'hsl(var(--state-handoff))',
            foreground: 'hsl(var(--state-handoff-foreground))',
            border: 'hsl(var(--state-handoff-border))',
            hover: 'hsl(var(--state-handoff-hover))',
            button: 'hsl(var(--state-handoff-button))',
            'button-hover': 'hsl(var(--state-handoff-button-hover))',
          },
          ai: {
            DEFAULT: 'hsl(var(--state-ai))',
            foreground: 'hsl(var(--state-ai-foreground))',
            border: 'hsl(var(--state-ai-border))',
            hover: 'hsl(var(--state-ai-hover))',
            button: 'hsl(var(--state-ai-button))',
            'button-hover': 'hsl(var(--state-ai-button-hover))',
            muted: 'hsl(var(--state-ai-muted))',
          },
          recording: {
            DEFAULT: 'hsl(var(--state-recording))',
            foreground: 'hsl(var(--state-recording-foreground))',
            dot: 'hsl(var(--state-recording-dot))',
            button: 'hsl(var(--state-recording-button))',
            'button-hover': 'hsl(var(--state-recording-button-hover))',
            hover: 'hsl(var(--state-recording-hover))',
          },
          unread: {
            DEFAULT: 'hsl(var(--state-unread))',
            border: 'hsl(var(--state-unread-border))',
          },
          'message-out': {
            DEFAULT: 'hsl(var(--state-message-out))',
            foreground: 'hsl(var(--state-message-out-foreground))',
            muted: 'hsl(var(--state-message-out-muted))',
          },
          document: 'hsl(var(--state-document))',
          audio: 'hsl(var(--state-audio))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['var(--font-barlow)', 'system-ui', 'sans-serif'],
        display: ['var(--font-fredoka)', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
