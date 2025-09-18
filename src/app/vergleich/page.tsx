'use client';

import React, { useState } from 'react';

import { MetadataUpload } from '@/src/app/vergleich/components/MetaDataUpload';
import { MetaValuesCalculator } from '@/src/app/vergleich/components/MetaValueCalculator';
import SimilarityResults from '@/src/app/vergleich/components/SimilarityResults';
import SimilaritySearch from '@/src/app/vergleich/components/SimilaritySearch';

export default function BahnVergleichPage() {
  const [results, setResults] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [originalId, setOriginalId] = useState<string>('');

  const handleSearch = async (
    id: string,
    bahnLimit: number,
    segmentLimit: number,
    weights: Record<string, number>,
  ) => {
    setIsLoading(true);
    setError('');
    setOriginalId(id);

    try {
      // Erstelle URL mit Gewichtungsparametern
      const params = new URLSearchParams({
        bahn_limit: bahnLimit.toString(),
        segment_limit: segmentLimit.toString(),
        weight_duration: weights.duration.toString(),
        weight_weight: weights.weight.toString(),
        weight_length: weights.length.toString(),
        weight_movement_type: weights.movement_type.toString(),
        weight_direction_x: weights.direction_x.toString(),
        weight_direction_y: weights.direction_y.toString(),
        weight_direction_z: weights.direction_z.toString(),
      });

      const response = await fetch(
        `http://localhost:8000/api/vergleich/aehnlichkeitssuche/${id}?${params.toString()}`,
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Extrahiere Daten aus der hierarchischen Struktur
      const allResults = [];

      // 1. Target-Bahn hinzufügen
      if (data.bahn_similarity?.target) {
        allResults.push(data.bahn_similarity.target);
      }

      // 2. Ähnliche Bahnen hinzufügen
      if (data.bahn_similarity?.similar_bahnen) {
        allResults.push(...data.bahn_similarity.similar_bahnen);
      }

      // 3. Alle Segment-Ergebnisse hinzufügen
      if (data.segment_similarity) {
        data.segment_similarity.forEach((segmentGroup: any) => {
          // Target-Segment hinzufügen
          if (segmentGroup.similarity_data?.target) {
            allResults.push(segmentGroup.similarity_data.target);
          }
          // Ähnliche Segmente hinzufügen
          if (segmentGroup.similarity_data?.similar_segmente) {
            allResults.push(...segmentGroup.similarity_data.similar_segmente);
          }
        });
      }

      setResults(allResults);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(`Fehler bei der Suche: ${errorMessage}`);
    }
    setIsLoading(false);
  };

  return (
    <div className="bg-gray-50">
      <div className="flex">
        {/* Left Sidebar */}
        <div className="h-fullscreen w-fit space-y-6 overflow-y-auto bg-white p-6 shadow-lg">
          <div>
            <h2 className="mb-4 text-xl font-bold text-gray-800">
              Tools & Konfiguration
            </h2>
            <div className="space-y-6">
              <MetaValuesCalculator />
              <MetadataUpload />
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="h-fullscreen flex-1 overflow-y-auto p-8">
          <div className="mx-auto max-w-6xl space-y-6">
            <div>
              <h1 className="mb-2 text-3xl font-bold text-gray-900">
                Ähnlichkeitssuche
              </h1>
              <p className="text-gray-600">
                Finden Sie ähnliche Bahnen und Segmente basierend auf 
                Feature-Analyse
              </p>
            </div>

            {/* Similarity Search Section */}
            <div className="space-y-6">
              <SimilaritySearch onSearch={handleSearch} />
              <SimilarityResults
                results={results}
                isLoading={isLoading}
                error={error}
                originalId={originalId}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
