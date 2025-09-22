// src/services/auswertung.segment.service.ts - Neuer Service

import { useEffect, useState } from 'react';

class AuswertungSegmentService {
  private selectedSegment: string = 'total';

  private listeners: Set<(segment: string) => void> = new Set();

  getSelectedSegment(): string {
    return this.selectedSegment;
  }

  setSelectedSegment(segment: string): void {
    this.selectedSegment = segment;
    this.notifyListeners();
  }

  resetSegment(): void {
    this.setSelectedSegment('total');
  }

  subscribe(listener: (segment: string) => void): () => void {
    this.listeners.add(listener);

    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notifyListeners(): void {
    this.listeners.forEach((listener) => listener(this.selectedSegment));
  }
}

// Singleton instance
export const segmentService = new AuswertungSegmentService();

// React Hook für Service
export function useSegmentService() {
  const [selectedSegment, setSelectedSegment] = useState(
    segmentService.getSelectedSegment(),
  );

  useEffect(() => {
    const unsubscribe = segmentService.subscribe(setSelectedSegment);
    return unsubscribe;
  }, []);

  return {
    selectedSegment,
    setSelectedSegment: segmentService.setSelectedSegment.bind(segmentService),
    resetSegment: segmentService.resetSegment.bind(segmentService),
  };
}
