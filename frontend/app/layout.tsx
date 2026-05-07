import type { Metadata } from 'next';
import './globals.css';
import QueryProvider from '@/components/QueryProvider';
import { AppLayout } from '@/components/AppLayout';

export const metadata: Metadata = {
  title: 'Nyaya Marga - Court Case Monitoring System',
  description:
    'AI-powered legal intelligence engine for the Centre for e-Governance, Karnataka. Upload court judgments, extract structured legal facts, and generate administrative action plans.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased text-slate-900 bg-slate-50">
        <QueryProvider>
          <AppLayout>{children}</AppLayout>
        </QueryProvider>
      </body>
    </html>
  );
}
