'use client';

import React, { useState } from 'react';
import { MetadataUpload } from '@/src/app/vergleich/components/MetaDataUpload';
import { MetaValuesCalculator } from '@/src/app/vergleich/components/MetaValueCalculator';
import SimilaritySearch from '@/src/app/vergleich/components/SimilaritySearch';
import SimilarityResults from '@/src/app/vergleich/components/SimilarityResults';

export default function BahnVergleichPage() {
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (id: string) => {
  setIsLoading(true);
  setError('');
  try {
    const response = await fetch(`http://localhost:8000/api/vergleich/aehnlichkeitssuche/${id}`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('API Response:', data); // Debug log
    
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
      data.segment_similarity.forEach(segmentGroup => {
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
    
    console.log('Processed Results:', allResults); // Debug log
    setResults(allResults);
    
  } catch (err) {
    console.error('Search error:', err);
    const errorMessage = (err instanceof Error) ? err.message : String(err);
    setError('Fehler bei der Suche: ' + errorMessage);
  }
  setIsLoading(false);
};

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex">
        {/* Left Sidebar */}
        <div className="w-80 bg-white shadow-lg p-6 space-y-6 overflow-y-auto max-h-screen">
          <div>
            <h2 className="text-xl font-bold text-gray-800 mb-4">Tools & Konfiguration</h2>
            <div className="space-y-6">
              <MetaValuesCalculator />
              <MetadataUpload />
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 p-8">
          <div className="max-w-6xl mx-auto space-y-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Ähnlichkeitssuche</h1>
              <p className="text-gray-600">Finden Sie ähnliche Bahnen und Segmente basierend auf komplexer Feature-Analyse</p>
            </div>
            
            {/* Similarity Search Section */}
            <div className="space-y-6">
              <SimilaritySearch onSearch={handleSearch} />
              <SimilarityResults results={results} isLoading={isLoading} error={error} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}