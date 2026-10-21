/* eslint-disable no-continue */
/* eslint-disable no-console */

'use server';

import type { MetricType } from '@/types/dashboard.types';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

function buildUrl(
  path: string,
  params: Record<string, string | string[] | undefined>,
) {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === '' || (Array.isArray(v) && v.length === 0))
      continue;
    if (Array.isArray(v)) {
      v.forEach((item) => parts.push(`${k}=${encodeURIComponent(item)}`));
    } else {
      parts.push(`${k}=${encodeURIComponent(v)}`);
    }
  }
  return parts.length
    ? `${API_BASE_URL}${path}?${parts.join('&')}`
    : `${API_BASE_URL}${path}`;
}

async function apiFetch(url: string) {
  const response = await fetch(url, {
    cache: 'no-cache',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok)
    throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

// Clears the backend's cached dashboard responses. Call before re-fetching
// on an explicit refresh action — otherwise the next fetch just hits the
// same cache key as before and returns the stale response.
export const refreshDashboardCache = async (): Promise<void> => {
  try {
    await fetch(`${API_BASE_URL}/dashboard/refresh`, { method: 'POST' });
  } catch (error) {
    console.error('Error clearing dashboard cache:', error);
  }
};

// Robots from motion.robot_info (robot filter options)
export const getRobots = async (): Promise<{
  robots: { robot_model: string; description: string | null }[];
}> => {
  try {
    return await apiFetch(`${API_BASE_URL}/dashboard/robots`);
  } catch (error) {
    console.error('Error fetching robots:', error);
    return { robots: [] };
  }
};

// robot: robot_model code, undefined = all robots
// tags (of the robot, if given) and the robots each tag contains
export const getAvailableTags = async (
  robot?: string,
): Promise<{ tags: string[]; robots: Record<string, string[]> }> => {
  try {
    return await apiFetch(buildUrl('/dashboard/tags', { robot }));
  } catch (error) {
    console.error('Error fetching tags:', error);
    return { tags: [], robots: {} };
  }
};

// Re-fetched on tag change (KPIs + distributions only)
export const getDashboardData = async (tags?: string[], robot?: string) => {
  try {
    return await apiFetch(buildUrl('/dashboard/data', { tag: tags, robot }));
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    return {};
  }
};

// with_trajectory=true → top 10 with trajectory points (WorkareaPlot)
// with_trajectory=false → top 100 without trajectories (PerformersTable, no tags)
//                       → top 5 without trajectories (PerformersTable, with tags)
export const getPerformers = async (
  metric: MetricType = 'sidtw',
  withTrajectory = false,
  tags?: string[],
  robot?: string,
) => {
  try {
    return await apiFetch(
      buildUrl('/dashboard/performers', {
        metric,
        with_trajectory: String(withTrajectory),
        tag: tags,
        robot,
      }),
    );
  } catch (error) {
    console.error('Error fetching performers:', error);
    return { bestPerformers: [], worstPerformers: [] };
  }
};

// one row per (tag, robot); robot undefined = rows of every robot
export const getTagInfo = async (tags?: string[], robot?: string) => {
  try {
    return await apiFetch(
      buildUrl('/dashboard/tag-info', { tag: tags, robot }),
    );
  } catch (error) {
    console.error('Error fetching tag info:', error);
    return { tags: [] };
  }
};

// On-demand: setpoints of the robot (and tags); from 2000 trajectories on a 1 % sample. Bounds with tags.
export const getWorkareaData = async (robot: string, tags?: string[]) => {
  try {
    return await apiFetch(
      buildUrl('/dashboard/workarea/data', { tag: tags, robot }),
    );
  } catch (error) {
    console.error('Error fetching workarea data:', error);
    return { points: [], bounds: null };
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

// Plotly mesh3d data: the robot's workspace envelope and (if available) the robot model
export const getRobotMesh = async (robot: string) => {
  try {
    return await apiFetch(
      buildUrl('/dashboard/workarea/robot-mesh', { robot }),
    );
  } catch (error) {
    console.error('Error fetching robot mesh:', error);
    return { mesh: null, model: null };
  }
};

// Returns pre-binned box-plot data per parameter from backend
export const getInfluenceBinned = async (
  metric: MetricType = 'sidtw',
  tags?: string[],
  robot?: string,
) => {
  try {
    return await apiFetch(
      buildUrl('/dashboard/influence/binned', { metric, tag: tags, robot }),
    );
  } catch (error) {
    console.error('Error fetching binned influence data:', error);
    return {};
  }
};
