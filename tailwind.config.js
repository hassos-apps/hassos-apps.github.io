/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',

  // Tell Tailwind where to look for class names to include in the build
  content: [
    './_layouts/**/*.{html,liquid}',
    './_includes/**/*.{html,liquid}',
    './_posts/**/*.{html,md}',
    './_apps/**/*.{html,md}',
    './*.html',
    './*.md',
    './assets/js/**/*.js',
  ],

  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },

  plugins: [],
}
