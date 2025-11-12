import { QuestionMarkCircleIcon, XMarkIcon } from '@heroicons/react/24/outline';
import React, { useState } from 'react';

const SearchHelpTooltip = () => {
  const [isOpen, setIsOpen] = useState(false);

  const handleClose = () => setIsOpen(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-1 text-gray-400 transition-colors hover:text-gray-600"
        type="button"
        aria-label="Suchhilfe anzeigen"
      >
        <QuestionMarkCircleIcon className="size-7" />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <button
            className="fixed inset-0 z-40 cursor-default"
            onClick={handleClose}
            onKeyDown={(e) => e.key === 'Escape' && handleClose()}
            type="button"
            aria-label="Tooltip schließen"
            tabIndex={-1}
          />

          {/* Tooltip */}
          <div className="absolute left-8 top-0 z-50 w-max rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
            <div className="mb-3 flex items-start justify-between">
              <h3 className="font-semibold text-gray-900">Suchhilfe</h3>
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600"
                type="button"
              >
                <XMarkIcon className="size-4" />
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div>
                <h4 className="mb-1 font-medium text-gray-700">
                  Einfache Suche:
                </h4>
                <ul className="space-y-1 text-gray-600">
                  <li>
                    • <code className="rounded bg-gray-100 px-1">123</code> -
                    Suche nach Bahn-ID
                  </li>
                  <li>
                    • <code className="rounded bg-gray-100 px-1">filename</code>{' '}
                    - Suche im Dateinamen
                  </li>
                </ul>
              </div>

              <div>
                <h4 className="mb-1 font-medium text-gray-700">
                  Filteroptionen:
                </h4>
                <ul className="space-y-1 text-gray-600">
                  <li>
                    • <code className="rounded bg-gray-100 px-1">n=5</code> oder{' '}
                    <code className="rounded bg-gray-100 px-1">np=5</code> -
                    Anzahl Segmente
                  </li>
                  <li>
                    •{' '}
                    <code className="rounded bg-gray-100 px-1">sidtw=0.5</code>{' '}
                    oder <code className="rounded bg-gray-100 px-1">s=0.5</code>{' '}
                    - SIDTW-Genauigkeit
                  </li>
                  <li>
                    • <code className="rounded bg-gray-100 px-1">w=2.5</code>{' '}
                    oder{' '}
                    <code className="rounded bg-gray-100 px-1">weight=2.5</code>{' '}
                    - Gewicht in kg (±0.5kg Toleranz)
                  </li>
                  <li>
                    • <code className="rounded bg-gray-100 px-1">v=250</code>{' '}
                    oder{' '}
                    <code className="rounded bg-gray-100 px-1">
                      velocity=250
                    </code>{' '}
                    - Geschwindigkeit
                  </li>
                  <li>
                    • <code className="rounded bg-gray-100 px-1">d=2024</code> -
                    Jahr, oder{' '}
                    <code className="rounded bg-gray-100 px-1">
                      d=09.07.2024
                    </code>{' '}
                    - Datum, oder{' '}
                    <code className="rounded bg-gray-100 px-1">
                      d=09.07.2024 17:52
                    </code>{' '}
                    - Datum mit Uhrzeit
                  </li>
                </ul>
              </div>

              <div className="border-t border-gray-200 pt-2">
                <p className="text-xs text-gray-500">
                  Tipp: Kombiniere mehrere Filter mit Leerzeichen, z.B.
                  <code className="ml-1 rounded bg-gray-100 px-1">
                    pick w=2.5 d=2024
                  </code>
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default SearchHelpTooltip;
