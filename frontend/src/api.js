import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API = `${BACKEND_URL}/api`;

export async function analyzeVideo(formData) {
  const response = await axios.post(`${API}/analyze`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function getAnalysisStatus(analysisId) {
  const response = await axios.get(`${API}/analysis/${analysisId}/status`);
  return response.data;
}

export async function getAnalysisResults(analysisId) {
  const response = await axios.get(`${API}/analysis/${analysisId}/results`);
  return response.data;
}

export function getPoseFrameUrl(analysisId, index) {
  return `${API}/analysis/${analysisId}/pose/frame/${index}`;
}

export function getVideoUrl(analysisId, type) {
  return `${API}/analysis/${analysisId}/video/${type}`;
}

export function getApiBaseUrl() {
  return API;
}
