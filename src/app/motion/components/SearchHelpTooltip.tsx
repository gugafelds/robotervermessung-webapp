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
        aria-label="Show search help"
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
            aria-label="Close tooltip"
            tabIndex={-1}
          />

          {/* Tooltip */}
          <div className="absolute left-8 top-0 z-50 w-max rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
            <div className="mb-3 flex items-start justify-between">
              <h3 className="font-semibold text-gray-900">Search Help</h3>
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
                  Basic search:
                </h4>
                <ul className="space-y-1 text-gray-600">
                  <li>
                    • <code className="rounded bg-gray-100 px-1">123</code> -
                    search by trajectory ID
                  </li>
                  <li>
                    • <code className="rounded bg-gray-100 px-1">filename</code>{' '}
                    - search in filename
                  </li>
                </ul>
              </div>

              <div>
                <h4 className="mb-1 font-medium text-gray-700">
                  Filter options:
                </h4>
                <ul className="space-y-1 text-gray-600">
                  <li>
                    • <code className="rounded bg-gray-100 px-1">n=5</code> or{' '}
                    <code className="rounded bg-gray-100 px-1">np=5</code> -
                    number of segments
                  </li>
                  <li>
                    •{' '}
                    <code className="rounded bg-gray-100 px-1">sidtw=0.5</code>{' '}
                    or <code className="rounded bg-gray-100 px-1">s=0.5</code> -
                    SIDTW accuracy
                  </li>
                  <li>
                    • <code className="rounded bg-gray-100 px-1">w=2.5</code> or{' '}
                    <code className="rounded bg-gray-100 px-1">weight=2.5</code>{' '}
                    - weight in kg (±0.5 kg tolerance)
                  </li>
                  <li>
                    • <code className="rounded bg-gray-100 px-1">v=250</code> or{' '}
                    <code className="rounded bg-gray-100 px-1">
                      velocity=250
                    </code>{' '}
                    - velocity
                  </li>
                  <li>
                    •{' '}
                    <code className="rounded bg-gray-100 px-1">t=tagname</code>{' '}
                    - filter by tag
                  </li>
                  <li>
                    • <code className="rounded bg-gray-100 px-1">d=2024</code> -
                    year, or{' '}
                    <code className="rounded bg-gray-100 px-1">
                      d=09.07.2024
                    </code>{' '}
                    - date, or{' '}
                    <code className="rounded bg-gray-100 px-1">
                      d=09.07.2024 17:52
                    </code>{' '}
                    - date with time
                  </li>
                </ul>
              </div>

              <div className="border-t border-gray-200 pt-2">
                <p className="text-xs text-gray-500">
                  Tip: Combine multiple filters with spaces, e.g.
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
