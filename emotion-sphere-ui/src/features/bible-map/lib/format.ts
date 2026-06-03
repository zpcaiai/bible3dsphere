export function formatYear(year: number): string {
  if (year < 0) return `${-year} BC`
  if (year === 0) return 'AD 1'
  return `AD ${year}`
}
