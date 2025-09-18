/* eslint-disable jsx-a11y/label-has-associated-control,no-await-in-loop */

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
  const [useBatchUpload, setUseBatchUpload] = useState<boolean>(true); // New state for batch upload toggle

  // State for segmentation method
  const [segmentationMethod, setSegmentationMethod] = useState<
    'fixed_segments' | 'reference_position'
  >('fixed_segments');

  const [numSegments, setNumSegments] = useState<number>(3); // Standardwert auf 3 gesetzt

  // Referenzposition Koordinaten
  const [referenceX, setReferenceX] = useState<string>('1250');
  const [referenceY, setReferenceY] = useState<string>('0');
  const [referenceZ, setReferenceZ] = useState<string>('1250');

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

    // Referenzposition als Array
    const referencePosition = [referenceX, referenceY, referenceZ];

    // If batch upload is selected and there are multiple files, use batch endpoint
    if (useBatchUpload && files.length > 0) {
      try {
        const formData = new FormData();

        // Add all files to the FormData
        for (let i = 0; i < files.length; i += 1) {
          formData.append('files', files[i]);
        }

        // Add other parameters
        formData.append('robot_model', robotModel);
        formData.append('bahnplanung', bahnplanung);
        formData.append('source_data_ist', sourceDataIst);
        formData.append('source_data_soll', sourceDataSoll);
        formData.append('upload_database', uploadDatabase.toString());
        formData.append('segmentation_method', segmentationMethod);
        formData.append('num_segments', numSegments.toString());

        // Add reference position parameters
        if (segmentationMethod === 'reference_position') {
          formData.append(
            'reference_position',
            JSON.stringify(referencePosition),
          );
        }

        // Send all files in one request
        const response = await fetch('/api/hochladen/process-csv-batch', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        setProcessingResults(result.file_results);

        // Generate summary message
        const totalSegments = result.file_results.reduce(
          (sum: number, r: ProcessingResult) => sum + r.segmentsFound,
          0,
        );
        const successfulFiles = result.file_results.filter(
          (r: ProcessingResult) => r.success,
        );
        const failedFiles = result.file_results.filter(
          (r: ProcessingResult) => !r.success,
        );

        let summaryMessage = '';
        if (successfulFiles.length > 0) {
          summaryMessage += `${successfulFiles.length} Datei(en) verarbeitet in ${result.processing_time_seconds.toFixed(2)} Sekunden.\n`;
          summaryMessage += `Insgesamt ${totalSegments} Bahnen gefunden.\n`;
        }

        if (failedFiles.length > 0) {
          setError(
            failedFiles
              .map((f: ProcessingResult) => `${f.filename}: ${f.error}`)
              .join('\n'),
          );
        }

        if (summaryMessage) {
          setSuccess(summaryMessage);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
        setProgress(100);
      }
    } else {
      // Original individual file upload logic
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
        formData.append('segmentation_method', segmentationMethod);
        formData.append('num_segments', numSegments.toString());

        // Add reference position parameters
        if (segmentationMethod === 'reference_position') {
          formData.append(
            'reference_position',
            JSON.stringify(referencePosition),
          );
        }

        try {
          const response = await fetch('/api/hochladen/process-csv', {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const result = await response.json();
          results.push({
            filename: file.name,
            segmentsFound: result.segments_found || result.data?.length || 0,
            success: true,
          });
        } catch (err) {
          results.push({
            filename: file.name,
            segmentsFound: 0,
            success: false,
            error: err instanceof Error ? err.message : 'Unknown error',
          });
        }

        processedFiles += 1;
        setProgress((processedFiles / totalFiles) * 100);
        setProcessingResults([...results]);
      }

      setIsLoading(false);

      // Generate summary message
      const totalSegments = results.reduce(
        (sum, r) => sum + r.segmentsFound,
        0,
      );
      const successfulFiles = results.filter((r) => r.success);
      const failedFiles = results.filter((r) => !r.success);

      let summaryMessage = '';
      if (successfulFiles.length > 0) {
        summaryMessage += `${successfulFiles.length} Datei(en) verarbeitet.\n`;
        summaryMessage += `Insgesamt ${totalSegments} Bahnen gefunden.\n`;
      }

      if (failedFiles.length > 0) {
        setError(
          failedFiles.map((f) => `${f.filename}: ${f.error}`).join('\n'),
        );
      }

      if (summaryMessage) {
        setSuccess(summaryMessage);
      }
    }
  };

  return (
    <div className="flex items-center stify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="mb-4 w-full max-w-lg rounded-xl bg-gray-100 p-4 shadow-md"
      >
        {/* File Input */}
        <div className="mb-2">
          <div className="text-xl font-bold text-primary">
            CSV-Uploader
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
          </div>
        </div>

        {/* Batch Upload Toggle */}
        <div className="mb-2">
          <label className="flex items-center" htmlFor="batch-upload">
            <input
              id="batch-upload"
              type="checkbox"
              className="size-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              checked={useBatchUpload}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setUseBatchUpload(e.target.checked)
              }
            />
            <span className="ml-2 text-sm font-light text-primary">
              Batch-Upload verwenden (schneller für mehrere Dateien)
            </span>
          </label>
        </div>

        <div className="mb-2">
          <label
            className="block px-1 text-base font-bold text-primary"
            htmlFor="robot-model"
          >
            Robotermodell
          </label>
          <input
            className="w-full appearance-none rounded border border-gray-400 p-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          <label
            className="block px-1 text-base font-bold text-primary"
            htmlFor="bahnplanung-input"
          >
            Bahnplanung
          </label>
          <input
            className="w-full appearance-none rounded border border-gray-400 p-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          <label
            className="block px-1 text-base font-bold text-primary"
            htmlFor="source-data-ist"
          >
            Quelle der Ist-Daten
          </label>
          <input
            className="w-full appearance-none rounded border border-gray-400 p-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
            id="source-data-ist"
            type="text"
            value={sourceDataIst}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setSourceDataIst(e.target.value)
            }
            placeholder="leica_at960"
            required
          />
        </div>
        <div className="mb-2">
          <label
            className="block px-1 text-base font-bold text-primary"
            htmlFor="source-data-soll"
          >
            Quelle der Soll-Daten
          </label>
          <input
            className="w-full appearance-none rounded border border-gray-400 p-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            <span className="ml-2 text-sm font-light text-primary">
              auf PostgreSQL hochladen
            </span>
          </label>
        </div>

        {/* Segmentation Method Selection (umbenannt) */}
        <div className="mb-2">
          <label className="mb-2 block text-base font-bold text-primary">
            Segmentierungsmethode
            <div className="mt-2">
              <label className="mr-4 inline-flex items-center font-light">
                <input
                  type="radio"
                  className="border-gray-300 text-blue-600 focus:ring-blue-500"
                  name="segmentationMethod"
                  value="fixed_segments"
                  checked={segmentationMethod === 'fixed_segments'}
                  onChange={(e) =>
                    setSegmentationMethod(
                      e.target.value as 'fixed_segments' | 'reference_position',
                    )
                  }
                />
                <span className="ml-2">
                  Feste Anzahl von Segmenten pro Bahn
                </span>
              </label>
              <label className="inline-flex items-center font-light">
                <input
                  type="radio"
                  className="border-gray-300 text-blue-600 focus:ring-blue-500"
                  name="segmentationMethod"
                  value="reference_position"
                  checked={segmentationMethod === 'reference_position'}
                  onChange={(e) =>
                    setSegmentationMethod(
                      e.target.value as 'fixed_segments' | 'reference_position',
                    )
                  }
                />
                <span className="ml-2">Nach Referenzposition teilen</span>
              </label>
            </div>
          </label>
        </div>

        {/* Referenzposition-Felder nur anzeigen, wenn 'reference_position' ausgewählt ist */}
        {segmentationMethod === 'reference_position' && (
          <div className="mb-4 rounded-md border border-gray-300 p-3">
            <label className="mb-2 block text-base font-bold text-primary">
              Referenzposition Koordinaten
              <div className="mt-2 grid grid-cols-3 gap-2">
                <div>
                  <label
                    className="block text-sm font-light text-primary"
                    htmlFor="reference-x"
                  >
                    X-Koordinate
                  </label>
                  <input
                    id="reference-x"
                    type="number"
                    step="0.1"
                    className="w-full appearance-none rounded border border-gray-400 px-2 py-1 text-sm leading-tight text-primary focus:outline-none focus:ring-1 focus:ring-blue-500"
                    value={referenceX}
                    onChange={(e) => setReferenceX(e.target.value)}
                  />
                </div>
                <div>
                  <label
                    className="block text-sm font-light text-primary"
                    htmlFor="reference-y"
                  >
                    Y-Koordinate
                  </label>
                  <input
                    id="reference-y"
                    type="number"
                    step="0.1"
                    className="w-full appearance-none rounded border border-gray-400 px-2 py-1 text-sm leading-tight text-primary focus:outline-none focus:ring-1 focus:ring-blue-500"
                    value={referenceY}
                    onChange={(e) => setReferenceY(e.target.value)}
                  />
                </div>
                <div>
                  <label
                    className="block text-sm font-light text-primary"
                    htmlFor="reference-z"
                  >
                    Z-Koordinate
                  </label>
                  <input
                    id="reference-z"
                    type="number"
                    step="0.1"
                    className="w-full appearance-none rounded border border-gray-400 px-2 py-1 text-sm leading-tight text-primary focus:outline-none focus:ring-1 focus:ring-blue-500"
                    value={referenceZ}
                    onChange={(e) => setReferenceZ(e.target.value)}
                  />
                </div>
              </div>
            </label>
          </div>
        )}

        {/* Number of Segments Input (nur angezeigt, wenn fixed_segments ausgewählt ist) */}
        {segmentationMethod === 'fixed_segments' && (
          <div className="mb-4">
            <label
              className="mb-2 block text-base font-bold text-primary"
              htmlFor="num-segments"
            >
              Anzahl der Segmente pro Bahn
              <input
                className="mt-2 w-full appearance-none rounded border p-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          <div className="mb-4 rounded border border-gray-400 bg-white p-4">
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
