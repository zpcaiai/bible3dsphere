import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '灵性决策陪伴 - SFDS',
  description: '一个反思性的决策支持系统，帮助您在决策中获得更深的自我觉察',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased min-h-screen bg-sfds-bg-primary">
        {children}
      </body>
    </html>
  );
}
