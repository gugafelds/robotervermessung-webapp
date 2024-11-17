'use server';

import { revalidatePath } from 'next/cache';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

async function fetchFromAPI(endpoint: string) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }
  return response.json();
}

export const getDashboardData = async () => {
  try {
    const result = await fetchFromAPI('/bahn/dashboard_data');
    revalidatePath('/dashboard');
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
