/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./**/*.html', './assets/js/**/*.js'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Bricolage Grotesque', 'system-ui', 'sans-serif'],
        hand: ['Caveat', 'cursive'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        kraft: '#E9DFC9',
        cream: '#F6EFDD',
        bark: '#3B2E22',
        forest: '#2F5D3A',
        mustard: '#D69A2D',
        brick: '#B0472F',
      },
    },
  },
};
