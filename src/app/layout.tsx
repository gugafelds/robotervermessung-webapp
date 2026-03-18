import '@/src/app/globals.css';

import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import type { ReactNode } from 'react';

import { Navbar } from '@/src/app/components/Navbar';

const inter = Inter({ subsets: ['latin'], display: 'swap' });

export const metadata: Metadata = {
  title: 'Robot Motion and Performance Database',
  description:
    'Web platform for the analysis and visualization of industrial robot motion and performance data.',
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
      <body className={`${inter.className} h-full`}>
        <Navbar />
        {children}
      </body>
    </html>
  );
}
