/**
 * HTML escape utility to prevent XSS when injecting user content into innerHTML.
 * Used in PDF/image export functions.
 */
export function escapeHtml(str) {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * Escape HTML but preserve line breaks as <br> for display.
 */
export function escapeHtmlWithBr(str) {
  if (!str) return ''
  return escapeHtml(str).replace(/\n/g, '<br>')
}
