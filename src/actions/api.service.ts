const API_BASE_URL = 'http://localhost:8000/api';

export async function fetchBahnInfo(bahnId: string) {
  const response = await fetch(`${API_BASE_URL}/bahn/bahn_info/${bahnId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch Bahn info');
  }
  return response.json();
}

export async function fetchBahnInfoCount() {
  const response = await fetch(`${API_BASE_URL}/bahn/bahn_info_count`);
  if (!response.ok) {
    throw new Error('Failed to fetch Bahn info count');
  }
  return response.json();
}
