'use client';

import React from 'react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="flex h-fullscreen justify-center overflow-y-auto p-6">
      {children}
    </main>
  );
}
