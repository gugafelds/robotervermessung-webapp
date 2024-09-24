import React from 'react';

export default function SegmentAnalyzerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <main className="grow bg-gray-100">
        <div className="container mx-auto px-4 py-8">{children}</div>
      </main>
    </div>
  );
}
