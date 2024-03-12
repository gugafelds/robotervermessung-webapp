import '@/src/app/globals.css';

import { SpeedInsights } from '@vercel/speed-insights/next';
import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import type { ReactNode } from 'react';

import { getTrajectories } from '@/src/actions/trajectory.service';
import { AppProvider } from '@/src/app/provider';
import { Navbar } from '@/src/components/Navbar';
import { json } from '@/src/lib/functions';
import { ModalsProvider } from '@/src/providers/slideover.provider';

const inter = Inter({ subsets: ['latin'], display: 'swap' });

export const metadata: Metadata = {
  title: 'robotervermessung',
  description: 'robots trajectories dataviz',
  manifest: '/manifest.json',
  icons: {
    shortcut: '/favicon.ico',
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
  const trajectories = await getTrajectories();

  return (
    <html lang="en">
      <head />
      <body className={inter.className}>
        <AppProvider trajectoriesDb={json(trajectories)}>
          <Navbar />
          <ModalsProvider>{children}</ModalsProvider>
          <SpeedInsights />
        </AppProvider>
      </body>
    </html>
  );
}
