import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ASC — Autonomous Sales Counterparty',
  description: 'Merchant-side autonomous AI commerce system with deterministic Commerce Control Plane',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
