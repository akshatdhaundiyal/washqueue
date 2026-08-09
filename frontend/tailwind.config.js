/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app.vue",
    "./app/app.vue",
    "./app/pages/**/*.vue",
    "./app/components/**/*.vue",
    "./app/layouts/**/*.vue",
    "./app/plugins/**/*.{js,ts}",
    "./nuxt.config.{js,ts}"
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
