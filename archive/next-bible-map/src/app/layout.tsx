import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '圣经地图 · Bible Map',
  description: '教学用途的圣经历史地理交互地图',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-[#0b1220] text-gray-200 antialiased">{children}</body>
    </html>
  )
}
