/** Tailwind 仅服务 bible-map feature；关闭 preflight 防止污染现有全局 CSS。 */
export default {
  content: ['./src/features/bible-map/**/*.{ts,tsx}'],
  corePlugins: { preflight: false },
  theme: { extend: {} },
  plugins: [],
}
