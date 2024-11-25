'use server';

import { revalidatePath } from 'next/cache';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

async function fetchFromAPI(endpoint: string) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    cache: 'no-store',  // Verhindert Caching
    next: {
      revalidate: 0 // Erzwingt Revalidierung
    }
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
    console.error('Error fetching dashboard data:', error);
    throw error;
  }
};

export const getCollectionSizes = async () => {
  try {
    const result = await fetchFromAPI('/bahn/collection_sizes');
    return result;
  } catch (error) {
    console.error('Error fetching collection sizes:', error);
    throw error;
  }
};

// Neue Funktion die beide Datensätze kombiniert holt
export const getAllDashboardData = async () => {
  try {
    const [dashboardData, collectionSizes] = await Promise.all([
      getDashboardData(),
      getCollectionSizes()
    ]);

    // Revalidiere erst nachdem alle Daten geholt wurden
    revalidatePath('/dashboard');

    return {
      dashboardData,
      collectionSizes
    };
  } catch (error) {
    console.error('Error fetching all dashboard data:', error);
    throw error;
  }
};