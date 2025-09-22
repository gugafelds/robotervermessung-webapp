// src/services/metrics.service.ts - Metriken Service

import { useCallback, useEffect, useState } from 'react';

import {
  getDFDPositionById,
  getDTWPositionById,
  getEAPositionById,
  getSIDTWPositionById,
} from '@/src/actions/auswertung.service';

interface MetricState {
  isLoaded: boolean;
  isLoading: boolean;
  visible: boolean;
}

interface MetricsState {
  ea: MetricState;
  dfd: MetricState;
  sidtw: MetricState;
  dtw: MetricState;
}

interface MetricData {
  ea: any[];
  dfd: any[];
  sidtw: any[];
  dtw: any[];
}

class MetricsService {
  private metrics: MetricsState = {
    ea: { isLoaded: false, isLoading: false, visible: false },
    dfd: { isLoaded: false, isLoading: false, visible: false },
    sidtw: { isLoaded: false, isLoading: false, visible: false },
    dtw: { isLoaded: false, isLoading: false, visible: false },
  };

  private data: MetricData = {
    ea: [],
    dfd: [],
    sidtw: [],
    dtw: [],
  };

  private listeners: Set<() => void> = new Set();

  getMetrics(): MetricsState {
    return { ...this.metrics };
  }

  getData(): MetricData {
    return { ...this.data };
  }

  async loadMetricData(
    metricType: 'ea' | 'dfd' | 'sidtw' | 'dtw',
    bahnId: string,
  ): Promise<void> {
    if (!bahnId) return;

    // Wenn bereits geladen, dann Toggle-Verhalten
    if (this.metrics[metricType].isLoaded) {
      this.metrics[metricType] = {
        ...this.metrics[metricType],
        visible: !this.metrics[metricType].visible,
      };
      this.notifyListeners();
      return;
    }

    this.metrics[metricType] = {
      ...this.metrics[metricType],
      isLoading: true,
    };
    this.notifyListeners();

    try {
      let data;
      switch (metricType) {
        case 'ea':
          data = await getEAPositionById(bahnId);
          this.data.ea = data;
          break;
        case 'dfd':
          data = await getDFDPositionById(bahnId);
          this.data.dfd = data;
          break;
        case 'sidtw':
          data = await getSIDTWPositionById(bahnId);
          this.data.sidtw = data;
          break;
        case 'dtw':
          data = await getDTWPositionById(bahnId);
          this.data.dtw = data;
          break;
        default:
          throw new Error(`Unhandled metric type: ${metricType}`);
      }

      this.metrics[metricType] = {
        isLoaded: true,
        isLoading: false,
        visible: true,
      };
    } catch (error) {
      this.metrics[metricType] = {
        ...this.metrics[metricType],
        isLoading: false,
      };
    }

    this.notifyListeners();
  }

  async loadAllMetrics(bahnId: string): Promise<void> {
    const promises = [
      this.loadMetricData('ea', bahnId),
      this.loadMetricData('dfd', bahnId),
      this.loadMetricData('sidtw', bahnId),
      this.loadMetricData('dtw', bahnId),
    ];

    await Promise.all(promises);
  }

  clearAllMetrics(): void {
    this.metrics = {
      ea: { isLoaded: false, isLoading: false, visible: false },
      dfd: { isLoaded: false, isLoading: false, visible: false },
      sidtw: { isLoaded: false, isLoading: false, visible: false },
      dtw: { isLoaded: false, isLoading: false, visible: false },
    };

    this.data = {
      ea: [],
      dfd: [],
      sidtw: [],
      dtw: [],
    };

    this.notifyListeners();
  }

  resetForNewBahn(): void {
    this.clearAllMetrics();
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);

    return () => {
      this.listeners.delete(listener);
    };
  }

  private notifyListeners(): void {
    this.listeners.forEach((listener) => listener());
  }
}

// Singleton instance
export const metricsService = new MetricsService();

// React Hook für Service
export function useMetricsService(bahnId: string) {
  const [metrics, setMetrics] = useState(metricsService.getMetrics());
  const [data, setData] = useState(metricsService.getData());

  useEffect(() => {
    const unsubscribe = metricsService.subscribe(() => {
      setMetrics(metricsService.getMetrics());
      setData(metricsService.getData());
    });
    return unsubscribe;
  }, []);

  // Reset wenn sich bahnId ändert
  useEffect(() => {
    metricsService.resetForNewBahn();
  }, [bahnId]);

  const loadMetricData = useCallback(
    (metricType: 'ea' | 'dfd' | 'sidtw' | 'dtw') => {
      return metricsService.loadMetricData(metricType, bahnId);
    },
    [bahnId],
  );

  const loadAllMetrics = useCallback(() => {
    return metricsService.loadAllMetrics(bahnId);
  }, [bahnId]);

  const clearAllMetrics = useCallback(() => {
    metricsService.clearAllMetrics();
  }, []);

  return {
    metrics,
    data,
    loadMetricData,
    loadAllMetrics,
    clearAllMetrics,
  };
}
