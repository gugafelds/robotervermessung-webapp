/* eslint-disable no-await-in-loop */

'use client';

import type { ChangeEvent, FormEvent } from 'react';
import React, { useState } from 'react';

type ProcessingResult = {
  filename: string;
  success: boolean;
  error?: string;
};

const ROSBAGProcessorForm: React.FC = () => {
  const [files, setFiles] = useState<FileList | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [processingResults, setProcessingResults] = useState<
    ProcessingResult[]
  >([]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!files?.length) {
      setError('Bitte wählen Sie mindestens eine rosbag-Datei aus.');
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccess('');
    setProgress(0);
    setProcessingResults([]);

    const results: ProcessingResult[] = [];

    for (let i = 0; i < files.length; i += 1) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/api/rosbag/process-rosbag', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const blob = await response.blob();
        const contentType = response.headers.get('content-type');
        const contentDisposition = response.headers.get('content-disposition');
        const fileName =
          contentDisposition?.split('filename=')[1].replace(/['"]/g, '') ||
          `${file.name}_processed${contentType?.includes('tar') ? '.tar.gz' : '.csv'}`;

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        results.push({ filename: file.name, success: true });
        setProgress(((i + 1) / files.length) * 100);
      } catch (err) {
        results.push({
          filename: file.name,
          success: false,
          error: err instanceof Error ? err.message : 'Unknown error',
        });
      }

      setProcessingResults([...results]);
    }

    setIsLoading(false);

    const successfulFiles = results.filter((r) => r.success);
    const failedFiles = results.filter((r) => !r.success);

    if (successfulFiles.length) {
      setSuccess(
        `${successfulFiles.length} rosbag-Datei(en) erfolgreich verarbeitet.\n${successfulFiles
          .map((r) => `\n${r.filename}: Erfolgreich`)
          .join('')}`,
      );
    }

    if (failedFiles.length) {
      setError(failedFiles.map((f) => `${f.filename}: ${f.error}`).join('\n'));
    }
  };

  return (
    <div className="flex h-full items-center justify-center">
      <form
        onSubmit={handleSubmit}
        className="mb-4 w-full max-w-lg rounded-xl bg-white px-8 pb-8 pt-6 shadow-md"
      >
        <h2 className="mb-6 text-xl font-bold text-primary">
          rosbag-Prozessor
        </h2>

        <div className="mb-4">
          <label
            className="mb-2 block text-base font-bold text-primary"
            htmlFor="file-input"
          >
            rosbag-Dateien
            <input
              className="w-full appearance-none rounded border px-3 py-2 font-light leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
              id="file-input"
              type="file"
              accept=".bag,.db3"
              multiple
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                if (e.target.files) setFiles(e.target.files);
                setProcessingResults([]);
              }}
              required
            />
          </label>
        </div>

        {processingResults.length > 0 && (
          <div className="mb-4 rounded border border-gray-200 p-4">
            <h3 className="mb-2 font-bold text-primary">Status:</h3>
            {processingResults.map((result) => (
              <div
                key={`${result.filename}-${Date.now()}`}
                className={`mb-1 text-sm ${
                  result.success ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {result.filename}: {result.success ? 'Erfolgreich' : 'Fehler!'}
              </div>
            ))}
          </div>
        )}

        {error && (
          <p className="mb-4 whitespace-pre-line text-xs italic text-red-500">
            {error}
          </p>
        )}
        {success && (
          <p className="mb-4 whitespace-pre-line text-sm italic text-green-900">
            {success}
          </p>
        )}

        {isLoading && (
          <div className="mb-4">
            <div className="mb-4 h-2.5 rounded-full bg-gray-200 dark:bg-gray-700">
              <div
                className="h-2.5 rounded-full bg-blue-600"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-center text-xs">{`${Math.round(progress)}% abgeschlossen`}</p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <button
            className="rounded bg-primary px-4 py-2 font-bold text-white transition duration-300 ease-in-out hover:bg-primary/80 focus:outline-none focus:ring-2 focus:ring-blue-500"
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? 'Wird verarbeitet...' : 'rosbag verarbeiten'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ROSBAGProcessorForm;
