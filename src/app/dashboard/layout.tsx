'use client';

import React from 'react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <main className="h-fullscreen overflow-y-auto p-6">{children}</main>;
}
