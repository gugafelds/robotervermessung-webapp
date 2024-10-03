import React from 'react';

export default function HochladenLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center">
      <main className="w-full max-w-4xl rounded-lg bg-white p-6">
        {children}
      </main>
    </div>
  );
}
