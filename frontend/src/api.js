import axios from 'axios';
import { mockStatus, mockResults, MOCK_ANALYSIS_ID } from './mocks/mockAnalysis';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API = `${BACKEND_URL}/api`;

export const isMockMode = () => {
  return (
    process.env.REACT_APP_MOCK_MODE === 'true' ||
    window.location.search.includes('mock=1')
  );
};

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function analyzeVideo(formData) {
  if (isMockMode()) {
    await wait(1500);
    return { analysis_id: MOCK_ANALYSIS_ID };
  }
  const response = await axios.post(`${API}/analyze`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function getAnalysisStatus(analysisId) {
  if (isMockMode()) {
    await wait(400);
    return mockStatus;
  }
  const response = await axios.get(`${API}/analysis/${analysisId}/status`);
  return response.data;
}

export async function getAnalysisResults(analysisId) {
  if (isMockMode()) {
    await wait(600);
    return mockResults;
  }
  const response = await axios.get(`${API}/analysis/${analysisId}/results`);
  return response.data;
}

export function getPoseFrameUrl(analysisId, index) {
  if (isMockMode()) {
    return mockResults.overlay_frames[index] || mockResults.overlay_frames[0];
  }
  return `${API}/analysis/${analysisId}/pose/frame/${index}`;
}

export function getVideoUrl(analysisId, type) {
  if (isMockMode()) {
    return null;
  }
  return `${API}/analysis/${analysisId}/video/${type}`;
}

export function getApiBaseUrl() {
  return API;
}
