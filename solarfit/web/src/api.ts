import type { AnalysisResult, SearchResult } from './types';

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';

export async function analyzeLocation(lat: number, lon: number): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/analyze?lat=${lat}&lon=${lon}`);
  if (!res.ok) throw new Error(`분석 실패: ${res.status}`);
  return res.json() as Promise<AnalysisResult>;
}

export async function searchAddress(query: string): Promise<SearchResult[]> {
  const res = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error(`검색 실패: ${res.status}`);
  const data = await res.json() as { results: SearchResult[] };
  return data.results;
}
