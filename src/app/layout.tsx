import '@/src/app/globals.css';

import { SpeedInsights } from '@vercel/speed-insights/next';
import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import type { ReactNode } from 'react';

import { Navbar } from '@/src/app/components/Navbar';

const inter = Inter({ subsets: ['latin'], display: 'swap' });

export const metadata: Metadata = {
  title: 'robotervermessung',
  description: 'robots trajectories dataviz',
  manifest: '/manifest.json',
  icons: {
    shortcut: '/favicon.ico',
    apple: [{ url: '/icons/apple-touch-icon.png', sizes: '180x180' }],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'robotervermessung',
  },
};

export const viewport: Viewport = {
  themeColor: '#3664FF',
};

export default async function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en">
      <head />
      <body className={inter.className}>
        <Navbar />
        {children}
        <SpeedInsights />
      </body>
    </html>
  );
}
