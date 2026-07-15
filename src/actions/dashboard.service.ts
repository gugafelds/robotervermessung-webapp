/* eslint-disable no-console */

'use server';

import type { MetricType } from '@/types/dashboard.types';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

function buildUrl(path: string, params: Record<string, string | string[] | undefined>) {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === '' || (Array.isArray(v) && v.length === 0)) continue;
    if (Array.isArray(v)) {
      v.forEach((item) => parts.push(`${k}=${encodeURIComponent(item)}`));
    } else {
      parts.push(`${k}=${encodeURIComponent(v)}`);
    }
  }
  return parts.length ? `${API_BASE_URL}${path}?${parts.join('&')}` : `${API_BASE_URL}${path}`;
}

async function apiFetch(url: string) {
  const response = await fetch(url, {
    cache: 'no-cache',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

export const getAvailableTags = async (): Promise<{ tags: string[] }> => {
  try {
    return await apiFetch(`${API_BASE_URL}/dashboard/tags`);
  } catch (error) {
    console.error('Error fetching tags:', error);
    return { tags: [] };
  }
};

// Re-fetched on tag change (KPIs + distributions only)
export const getDashboardData = async (tags?: string[]) => {
  try {
    return await apiFetch(buildUrl('/dashboard/data', { tag: tags }));
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    return {};
  }
};

// with_trajectory=true → top 10 with trajectory points (WorkareaPlot)
// with_trajectory=false → top 100 without trajectories (PerformersTable, no tags)
//                       → top 5 without trajectories (PerformersTable, with tags)
export const getPerformers = async (metric: MetricType = 'sidtw', withTrajectory = false, tags?: string[]) => {
  try {
    return await apiFetch(buildUrl('/dashboard/performers', { metric, with_trajectory: String(withTrajectory), tag: tags }));
  } catch (error) {
    console.error('Error fetching performers:', error);
    return { bestPerformers: [], worstPerformers: [] };
  }
};

export const getTagInfo = async (tags?: string[]) => {
  try {
    return await apiFetch(buildUrl('/dashboard/tag-info', { tag: tags }));
  } catch (error) {
    console.error('Error fetching tag info:', error);
    return { tags: [] };
  }
};

// Returns all points with tag field — loaded once, filtered client-side
export const getWorkareaData = async () => {
  try {
    return await apiFetch(`${API_BASE_URL}/dashboard/workarea`);
  } catch (error) {
    console.error('Error fetching workarea data:', error);
    return { points: [] };
  }
};

// Returns per (date, tag) rows — loaded once per metric, aggregated client-side
export const getMetricTimeline = async (metric: MetricType = 'sidtw') => {
  try {
    return await apiFetch(buildUrl('/dashboard/timeline', { metric }));
  } catch (error) {
    console.error('Error fetching timeline:', error);
    return { timeline: [] };
  }
};

// Returns 5000 samples with tag field — loaded once per metric, filtered client-side
export const getMetricInfluence = async (metric: MetricType = 'sidtw') => {
  try {
    return await apiFetch(buildUrl('/dashboard/influence', { metric }));
  } catch (error) {
    console.error('Error fetching influence data:', error);
    return { data: [] };
  }
};
