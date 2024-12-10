'use server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

/* eslint-disable no-await-in-loop */
async function streamFromAPI(endpoint: string) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`);
  if (!response.body) throw new Error('No response body');

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];

  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  return JSON.parse(new TextDecoder().decode(Buffer.concat(chunks)));
}
/* eslint-enable no-await-in-loop */

async function fetchFromAPI(endpoint: string, useStream = false) {
  if (useStream) {
    return streamFromAPI(endpoint);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    cache: 'no-cache',
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }
  return response.json();
}

export const getDashboardData = async () => {
  try {
    const result = await fetchFromAPI('/bahn/dashboard_data');
    return result;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching dashboard data:', error);
    throw error;
  }
};

export const getCollectionSizes = async () => {
  try {
    const result = await fetchFromAPI('/bahn/collection_sizes');
    return result;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching collection sizes:', error);
    throw error;
  }
};
