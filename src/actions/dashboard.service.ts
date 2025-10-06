/* eslint-disable no-console */

'use server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

// Vereinfachte Funktion zum Abrufen der Dashboard-Daten
export const getDashboardData = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/bahn/dashboard_data`, {
      cache: 'no-cache', // Kein Caching für konsistente Ergebnisse
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(
        `API request failed: ${response.status} ${response.statusText}`,
      );
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    // Leeres Objekt zurückgeben, damit der Client mit Standardwerten arbeiten kann
    return {};
  }
};

// Funktion zum Abrufen der Arbeitsraum-Daten
export const getWorkareaData = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/bahn/dashboard_workarea`, {
      cache: 'no-cache',
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(
        `API request failed: ${response.status} ${response.statusText}`,
      );
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching workarea data:', error);
    return { points: [] };
  }
};
