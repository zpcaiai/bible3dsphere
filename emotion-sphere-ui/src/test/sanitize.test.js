/**
 * Tests for src/sanitize.js — XSS prevention utilities.
 */
import { describe, it, expect } from 'vitest'
import { escapeHtml, escapeHtmlWithBr } from '../sanitize'

describe('escapeHtml', () => {
  it('escapes ampersand', () => {
    expect(escapeHtml('a & b')).toBe('a &amp; b')
  })

  it('escapes less-than and greater-than', () => {
    expect(escapeHtml('<script>alert(1)</script>')).toBe(
      '&lt;script&gt;alert(1)&lt;/script&gt;'
    )
  })

  it('escapes double quotes', () => {
    expect(escapeHtml('"hello"')).toBe('&quot;hello&quot;')
  })

  it('escapes single quotes', () => {
    expect(escapeHtml("it's")).toBe('it&#39;s')
  })

  it('handles empty/falsy input', () => {
    expect(escapeHtml('')).toBe('')
    expect(escapeHtml(null)).toBe('')
    expect(escapeHtml(undefined)).toBe('')
  })

  it('handles non-string input by coercing to string', () => {
    expect(escapeHtml(42)).toBe('42')
  })

  it('leaves safe text unchanged', () => {
    expect(escapeHtml('Hello 你好 世界')).toBe('Hello 你好 世界')
  })

  it('escapes a full XSS payload', () => {
    const payload = '<img src=x onerror="alert(\'xss\')">'
    const escaped = escapeHtml(payload)
    expect(escaped).not.toContain('<img')
    expect(escaped).toContain('&lt;img')
    expect(escaped).toContain('onerror=&quot;alert(&#39;xss&#39;)&quot;')
  })
})

describe('escapeHtmlWithBr', () => {
  it('converts newlines to <br>', () => {
    expect(escapeHtmlWithBr('line1\nline2')).toBe('line1<br>line2')
  })

  it('still escapes HTML in the text', () => {
    expect(escapeHtmlWithBr('<b>bold</b>\nnext')).toBe(
      '&lt;b&gt;bold&lt;/b&gt;<br>next'
    )
  })

  it('handles empty/falsy input', () => {
    expect(escapeHtmlWithBr('')).toBe('')
    expect(escapeHtmlWithBr(null)).toBe('')
  })
})
