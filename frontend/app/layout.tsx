import './globals.css'

export const metadata = {
  title: 'HVAC Pricing Intelligence AI',
  description: 'HVAC price import, comparison, and bid intelligence',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
