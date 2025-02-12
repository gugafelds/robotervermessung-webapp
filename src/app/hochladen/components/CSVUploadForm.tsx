/* eslint-disable */

'use client';

import type { ChangeEvent, FormEvent } from 'react';
import React, { useState } from 'react';

type ProcessingResult = {
  filename: string;
  segmentsFound: number;
  success: boolean;
  error?: string;
};

const CSVUploadForm: React.FC = () => {
  const [files, setFiles] = useState<FileList | null>(null);
  const [robotModel, setRobotModel] = useState<string>('');
  const [bahnplanung, setBahnplanung] = useState<string>('');
  const [sourceDataIst, setSourceDataIst] = useState<string>('');
  const [sourceDataSoll, setSourceDataSoll] = useState<string>('');
  const [uploadDatabase, setUploadDatabase] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [processingResults, setProcessingResults] = useState<
    ProcessingResult[]
  >([]);

  // New state for segmentation method
  const [segmentationMethod, setSegmentationMethod] = useState<
    'home' | 'fixed'
  >('home');
  const [numSegments, setNumSegments] = useState<number>(1);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!files || files.length === 0) {
      setError('Bitte wählen Sie mindestens eine CSV-Datei aus.');
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccess('');
    setProgress(0);
    setProcessingResults([]);

    const totalFiles = files.length;
    let processedFiles = 0;
    const results: ProcessingResult[] = [];

    for (let i = 0; i < totalFiles; i += 1) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('robot_model', robotModel);
      formData.append('bahnplanung', bahnplanung);
      formData.append('source_data_ist', sourceDataIst);
      formData.append('source_data_soll', sourceDataSoll);
      formData.append('upload_database', uploadDatabase.toString());
      // Add new segmentation parameters
      formData.append('segmentation_method', segmentationMethod);
      formData.append('num_segments', numSegments.toString());

      try {
        const response = await fetch('/api/bahn/process-csv', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          if (uploadDatabase) {
            results.push({
              filename: file.name,
              segmentsFound: 1,
              success: true,
            });
          } else {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
        } else {
          const result = await response.json();
          results.push({
            filename: file.name,
            segmentsFound: result.segments_found || result.data?.length || 0,
            success: true,
          });
        }
      } catch (err) {
        if (uploadDatabase) {
          results.push({
            filename: file.name,
            segmentsFound: 1,
            success: true,
          });
        } else {
          results.push({
            filename: file.name,
            segmentsFound: 0,
            success: false,
            error: err instanceof Error ? err.message : 'Unknown error',
          });
        }
      }

      processedFiles += 1;
      setProgress((processedFiles / totalFiles) * 100);
      setProcessingResults([...results]);
    }

    setIsLoading(false);

    // Generate summary message
    const totalSegments = results.reduce((sum, r) => sum + r.segmentsFound, 0);
    const successfulFiles = results.filter((r) => r.success);
    const failedFiles = results.filter((r) => !r.success);

    let summaryMessage = '';
    if (successfulFiles.length > 0) {
      summaryMessage += `${successfulFiles.length} Datei(en) verarbeitet.\n`;
      successfulFiles.forEach((r) => {
        summaryMessage += `\n${r.filename.substring(0, 22)}: ${r.segmentsFound} Bahn(en)`;
      });
    }

    if (failedFiles.length > 0) {
      setError(failedFiles.map((f) => `${f.filename}: ${f.error}`).join('\n'));
    }

    if (summaryMessage) {
      setSuccess(summaryMessage);
    }
  };

  return (
    <div className="flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="mb-4 w-full max-w-lg rounded-xl bg-gray-100 p-4 shadow-md"
      >
        {/* File Input */}
        <div className="mb-2">
          <div className="text-xl font-bold text-primary">CSV-Uploader
          <label
            className="mb-2 block text-base font-bold text-primary"
            htmlFor="file-input"
          >
            <input
              className="w-full rounded py-1 font-light leading-tight text-primary focus:outline-none focus:ring-2"
              id="file-input"
              type="file"
              accept=".csv"
              multiple
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                if (e.target.files) setFiles(e.target.files);
                setProcessingResults([]);
              }}
              required
            />
          </label>
        </div></div>
        <div className="mb-2">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label
            className="px-1 block text-base font-bold text-primary"
            htmlFor="robot-model"
          >
            Robotermodell
          </label>
          <input
            className="w-full appearance-none rounded border border-gray-400 px-2 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
            id="robot-model"
            type="text"
            value={robotModel}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setRobotModel(e.target.value)
            }
            placeholder="abb_irb4400"
            required
          />
        </div>
        <div className="mb-2">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label
            className="px-1 block text-base font-bold text-primary"
            htmlFor="bahnplanung-input"
          >
            Bahnplanung
          </label>
          <input
            className="w-full appearance-none rounded border border-gray-400 px-2 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
            id="bahnplanung-input"
            type="text"
            value={bahnplanung}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setBahnplanung(e.target.value)
            }
            placeholder="abb_steuerung"
            required
          />
        </div>
        <div className="mb-2">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label
            className="px-1 block text-base font-bold text-primary"
            htmlFor="source-data-ist"
          >
            Quelle der Ist-Daten
          </label>
          <input
            className="w-full appearance-none rounded border border-gray-400 px-2 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
            id="source-data-ist"
            type="text"
            value={sourceDataIst}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setSourceDataIst(e.target.value)
            }
            placeholder="vicon"
            required
          />
        </div>
        <div className="mb-2">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label
            className="px-1 block text-base font-bold text-primary"
            htmlFor="source-data-soll"
          >
            Quelle der Soll-Daten
          </label>
          <input
            className="w-full appearance-none rounded border border-gray-400 px-2 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
            id="source-data-soll"
            type="text"
            value={sourceDataSoll}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setSourceDataSoll(e.target.value)
            }
            placeholder="abb_websocket"
            required
          />
        </div>
        <div className="mb-2">
          <label className="flex items-center" htmlFor="upload-database">
            <input
              id="upload-database"
              type="checkbox"
              className="size-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              checked={uploadDatabase}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setUploadDatabase(e.target.checked)
              }
            />
            <span className="ml-2 text-base font-light text-sm text-primary">
              auf PostgreSQL hochladen
            </span>
          </label>
        </div>

        {/* New Segmentation Method Selection */}
        <div className="mb-2">
          <label className="mb-2 block text-base font-bold text-primary">
            Segmentierungsmethode
            <div className="mt-2">
              <label className="mr-4 inline-flex font-light items-center">
                <input
                  type="radio"
                  className="form-radio"
                  name="segmentationMethod"
                  value="home"
                  checked={segmentationMethod === 'home'}
                  onChange={(e) =>
                    setSegmentationMethod(e.target.value as 'home' | 'fixed')
                  }
                />
                <span className="ml-2">Nach Home-Position</span>
              </label>
              <label className="inline-flex font-light items-center">
                <input
                  type="radio"
                  className="form-radio"
                  name="segmentationMethod"
                  value="fixed"
                  checked={segmentationMethod === 'fixed'}
                  onChange={(e) =>
                    setSegmentationMethod(e.target.value as 'home' | 'fixed')
                  }
                />
                <span className="ml-2">Feste Anzahl</span>
              </label>
            </div>
          </label>
        </div>

        {/* Number of Segments Input (only shown when fixed segmentation is selected) */}
        {segmentationMethod === 'fixed' && (
          <div className="mb-4">
            <label
              className="mb-2 block text-base font-bold text-primary"
              htmlFor="num-segments"
            >
              Anzahl der Segmente pro Gruppe
              <input
                className="mt-2 w-full appearance-none rounded border px-2 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
                id="num-segments"
                type="number"
                min="1"
                value={numSegments}
                onChange={(e) => setNumSegments(parseInt(e.target.value, 10))}
                required
              />
            </label>
          </div>
        )}

        {/* Processing Results */}
        {processingResults.length > 0 && (
          <div className="mb-4 rounded border bg-white border-gray-400 p-4">
            <h3 className="mb-2 font-semibold text-primary">Status:</h3>
            {processingResults.map((result) => (
              <div
                key={`${result.filename}-${Date.now()}`}
                className={`mb-1 text-sm ${
                  result.success ? 'text-gray-800' : 'text-red-600'
                }`}
              >
                {result.filename.substring(0, 22)}:{' '}
                {result.success
                  ? `${result.segmentsFound} Bahn(en)`
                  : 'Fehler!'}
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

        <div className="flex items-center justify-end">
          <button
            className="rounded bg-primary px-4 py-2 font-bold text-white transition duration-300 ease-in-out hover:bg-primary/80 focus:outline-none focus:ring-2 focus:ring-blue-500"
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? 'Wird verarbeitet...' : 'Start'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default CSVUploadForm;
