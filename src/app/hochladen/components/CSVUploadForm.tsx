'use client';

import type { ChangeEvent, FormEvent } from 'react';
import React, { useState } from 'react';

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

  const API_BASE_URL = 'http://localhost:8000/api';

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

    const totalFiles = files.length;
    let processedFiles = 0;

    for (let i = 0; i < totalFiles; i += 1) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('robot_model', robotModel);
      formData.append('bahnplanung', bahnplanung);
      formData.append('source_data_ist', sourceDataIst);
      formData.append('source_data_soll', sourceDataSoll);
      formData.append('upload_database', uploadDatabase.toString());

      try {
        // eslint-disable-next-line no-await-in-loop
        const response = await fetch(`${API_BASE_URL}/bahn/process-csv`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // eslint-disable-next-line no-await-in-loop
        const result = await response.json();
        // eslint-disable-next-line no-console
        console.log(`CSV ${file.name} processed successfully:`, result);
        processedFiles += 1;
        setProgress((processedFiles / totalFiles) * 100);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error(`Error processing CSV ${file.name}:`, err);
        setError((prev) => `${prev}Fehler beim Verarbeiten von ${file.name}. `);
      }
    }

    if (processedFiles === totalFiles) {
      setSuccess(
        `${processedFiles} CSV-Datei(en) wurden erfolgreich verarbeitet und hochgeladen.`,
      );
    } else {
      setSuccess(
        `${processedFiles} von ${totalFiles} CSV-Datei(en) wurden erfolgreich verarbeitet.`,
      );
    }
    setIsLoading(false);
  };

  return (
    <div className="flex h-full items-center justify-center">
      <form
        onSubmit={handleSubmit}
        className="mb-4 w-full max-w-lg rounded-xl bg-white px-8 pb-8 pt-6 shadow-md"
      >
        <div className="mb-4">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label
            className="mb-2 block text-base font-bold text-primary"
            htmlFor="file-input"
          >
            CSV-Dateien
          </label>
          <input
            className="w-full appearance-none rounded border px-3 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
            id="file-input"
            type="file"
            accept=".csv"
            multiple
            onChange={(e: ChangeEvent<HTMLInputElement>) => {
              if (e.target.files) setFiles(e.target.files);
            }}
            required
          />
        </div>
        <div className="mb-4">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label
            className="mb-2 block text-base font-bold text-primary"
            htmlFor="robot-model"
          >
            Roboter
          </label>
          <input
            className="w-full appearance-none rounded border px-3 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
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
        <div className="mb-4">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label
            className="mb-2 block text-base font-bold text-primary"
            htmlFor="bahnplanung-input"
          >
            Bahnplanung
          </label>
          <input
            className="w-full appearance-none rounded border px-3 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
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
        <div className="mb-4">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label
            className="mb-2 block text-base font-bold text-primary"
            htmlFor="source-data-ist"
          >
            Quelle der Ist-Daten
          </label>
          <input
            className="w-full appearance-none rounded border px-3 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
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
        <div className="mb-4">
          {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
          <label
            className="mb-2 block text-base font-bold text-primary"
            htmlFor="source-data-soll"
          >
            Quelle der Soll-Daten
          </label>
          <input
            className="w-full appearance-none rounded border px-3 py-2 leading-tight text-primary focus:outline-none focus:ring-2 focus:ring-blue-500"
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
        <div className="mb-6">
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
            <span className="ml-2 text-base font-bold text-primary">
              auf PostgreSQL hochladen
            </span>
          </label>
        </div>
        {error && <p className="mb-4 text-xs italic text-red-500">{error}</p>}
        {success && (
          <p className="mb-4 text-xs italic text-green-500">{success}</p>
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
            {isLoading ? 'Wird hochgeladen...' : 'Dateien hochladen'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default CSVUploadForm;
