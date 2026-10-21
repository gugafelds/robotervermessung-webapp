'use client';

import type { FormEvent, ReactNode } from 'react';
import React, { useEffect, useState } from 'react';

interface PasswordDialogProps {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  // runs the protected action; returns an error message (dialog stays open) or nothing (dialog closes)
  onConfirm: (password: string) => Promise<string | void>;
  onClose: () => void;
}

// Asks for the admin password before a destructive action. The backend checks it (ADMIN_PASSWORD).
export const PasswordDialog: React.FC<PasswordDialogProps> = ({
  open,
  title,
  message,
  confirmLabel,
  danger = false,
  onConfirm,
  onClose,
}) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setPassword('');
      setError('');
    }
  }, [open]);

  if (!open) return null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!password || busy) return;
    setBusy(true);
    const result = await onConfirm(password);
    setBusy(false);
    if (result) setError(result);
    else onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <form
        onSubmit={submit}
        className="w-96 rounded-xl border border-gray-500 bg-white p-6 shadow-lg"
      >
        <h3 className="mb-2 text-lg font-bold text-primary">{title}</h3>
        <div className="mb-4 text-sm text-gray-600">{message}</div>
        <input
          type="password"
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
          autoComplete="current-password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!password || busy}
            className={`rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-40 ${
              danger
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-blue-950 hover:bg-blue-800'
            }`}
          >
            {busy ? 'Please wait…' : confirmLabel}
          </button>
        </div>
      </form>
    </div>
  );
};
