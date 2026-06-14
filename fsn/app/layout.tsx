import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'FSN Mission Control',
  description: 'Federated Survival Network Dashboard',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
