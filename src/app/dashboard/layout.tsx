'use client';

import React from 'react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="flex h-fullscreen flex-col overflow-y-auto bg-gray-50 p-6">
      {children}
    </main>
  );
}
