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
        // shadcn/ui CSS variables
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
        // Paleta Revoluna - baseada em #C82D37
        revoluna: {
          50: '#FADCDE', // Rosa Suave
          100: '#F5B8BC',
          200: '#E85A63', // Vermelho Claro
          300: '#D64550',
          400: '#C82D37', // Vermelho Principal (PRIMARY)
          500: '#C82D37', // Base
          600: '#A52530', // Vermelho Médio
          700: '#7A1B22', // Vermelho Escuro
          800: '#5A1419',
          900: '#3A0D10',
        },
        // Cores de apoio
        gray: {
          50: '#F7F7F7', // Off-White
          100: '#E2E8F0', // Cinza Claro
          200: '#CBD5E0',
          300: '#A0AEC0',
          400: '#718096',
          500: '#4A5568', // Cinza Médio
          600: '#2D3748', // Cinza Escuro
          700: '#1A202C',
          800: '#171923',
          900: '#0D1117',
        },
        // Cores semânticas
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
        // Cores de apoio extras
        gold: '#D4A853',
        teal: '#2D8C7A',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
