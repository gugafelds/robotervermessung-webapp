'use client';

import React, { useEffect, useState } from 'react';

import { Typography } from '@/src/components/Typography';

// Mock data - replace with actual data fetching
const mockFiles = [
  { id: 1, name: 'Record_001.csv' },
  { id: 2, name: 'Record_002.csv' },
  { id: 3, name: 'Record_003.csv' },
];

const mockEvents = [
  { id: 1, time: 0, name: 'Start' },
  { id: 2, time: 25, name: 'Position 1' },
  { id: 3, time: 50, name: 'Position 2' },
  { id: 4, time: 75, name: 'Position 3' },
  { id: 5, time: 100, name: 'End' },
];

const mockAnalysis = {
  duration: 75,
  averageSpeed: 1.5,
  maxAcceleration: 2.3,
  pointCount: 1500,
};

export const TrajectorySegmentAnalyzer = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [events, setEvents] = useState([]);
  const [selectedSegment, setSelectedSegment] = useState({
    start: null,
    end: null,
  });
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    // Simulating data fetching when a file is selected
    if (selectedFile) {
      setEvents(mockEvents);
    }
  }, [selectedFile]);

  useEffect(() => {
    // Simulating analysis when a segment is selected
    if (selectedSegment.start && selectedSegment.end) {
      setAnalysis(mockAnalysis);
    }
  }, [selectedSegment]);

  const handleFileSelect = (event) => {
    const fileId = parseInt(event.target.value);
    setSelectedFile(mockFiles.find((file) => file.id === fileId));
    setSelectedSegment({ start: null, end: null });
    setAnalysis(null);
  };

  const handleSegmentSelect = (event, point) => {
    const eventId = parseInt(event.target.value);
    const selectedEvent = events.find((e) => e.id === eventId);
    setSelectedSegment((prev) => ({ ...prev, [point]: selectedEvent }));
  };

  return (
    <div className="rounded-lg bg-white p-6 shadow-md">
      <Typography as="h2" className="mb-4 text-xl font-semibold">
        Select Record File
      </Typography>
      <select onChange={handleFileSelect} className="w-full rounded border p-2">
        <option value="">Select a file</option>
        {mockFiles.map((file) => (
          <option key={file.id} value={file.id}>
            {file.name}
          </option>
        ))}
      </select>

      {selectedFile && (
        <>
          <Typography as="h2" className="mb-4 mt-6 text-xl font-semibold">
            Select Segment
          </Typography>
          <div className="mb-4 flex justify-between">
            <div>
              <label className="mb-2 block">Start Point</label>
              <select
                onChange={(e) => handleSegmentSelect(e, 'start')}
                className="w-full rounded border p-2"
              >
                <option value="">Select start point</option>
                {events.map((event) => (
                  <option key={event.id} value={event.id}>
                    {event.name} (t={event.time})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block">End Point</label>
              <select
                onChange={(e) => handleSegmentSelect(e, 'end')}
                className="w-full rounded border p-2"
              >
                <option value="">Select end point</option>
                {events.map((event) => (
                  <option key={event.id} value={event.id}>
                    {event.name} (t={event.time})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mb-6 mt-4">
            <div className="h-4 w-full rounded-full bg-gray-200">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="absolute h-4 w-2 rounded-full bg-blue-500"
                  style={{ left: `${event.time}%` }}
                  title={`${event.name} (t=${event.time})`}
                />
              ))}
            </div>
          </div>
        </>
      )}

      {analysis && (
        <>
          <Typography as="h2" className="mb-4 mt-6 text-xl font-semibold">
            Segment Analysis
          </Typography>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded bg-gray-100 p-4">
              <Typography as="h3" className="font-semibold">
                Duration
              </Typography>
              <Typography>{analysis.duration} seconds</Typography>
            </div>
            <div className="rounded bg-gray-100 p-4">
              <Typography as="h3" className="font-semibold">
                Average Speed
              </Typography>
              <Typography>{analysis.averageSpeed} m/s</Typography>
            </div>
            <div className="rounded bg-gray-100 p-4">
              <Typography as="h3" className="font-semibold">
                Max Acceleration
              </Typography>
              <Typography>{analysis.maxAcceleration} m/s²</Typography>
            </div>
            <div className="rounded bg-gray-100 p-4">
              <Typography as="h3" className="font-semibold">
                Point Count
              </Typography>
              <Typography>{analysis.pointCount}</Typography>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
