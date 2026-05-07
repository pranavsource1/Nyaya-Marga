/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
      },
      colors: {
        /* ─── Government Deep Navy — primary authority color ─── */
        gov: {
          50:  '#f0f3f9',
          100: '#dce3f0',
          200: '#b9c7e1',
          300: '#8da4cc',
          400: '#6280b4',
          500: '#3d5a8a',
          600: '#2d4470',
          700: '#1e3358',
          800: '#1a2744',
          900: '#111b30',
          950: '#0a1019',
        },
        /* ─── Karnataka Gold — pending / warnings / branding accent ─── */
        'ka-gold': {
          50:  '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        /* ─── Karnataka Crimson — high urgency / errors / appeal status ─── */
        'ka-crimson': {
          50:  '#fff1f2',
          100: '#ffe4e6',
          200: '#fecdd3',
          300: '#fda4af',
          400: '#fb7185',
          500: '#f43f5e',
          600: '#e11d48',
          700: '#be123c',
          800: '#9f1239',
          900: '#881337',
        },
        /* ─── Compliant Emerald — approved / verified status ─── */
        'ka-green': {
          50:  '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
      },
      /* ─── Strict Gov border radii — no rounded-xl anywhere ─── */
      borderRadius: {
        'gov': '2px',
        'gov-sm': '1px',
      },
      /* ─── Dense spacing tokens ─── */
      spacing: {
        '4.5': '1.125rem',
        '13': '3.25rem',
        '15': '3.75rem',
        '18': '4.5rem',
      },
      fontSize: {
        'xxs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
    },
  },
  plugins: [],
};
