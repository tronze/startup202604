import { useState } from 'react';
import type { AnalysisResult } from './types';
import { analyzeLocation } from './api';
import SearchBar from './components/SearchBar';
import Map2D from './components/Map2D';
import AnalysisPanel from './components/AnalysisPanel';

export default function App() {
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSelect(lat: number, lon: number) {
    setCoords({ lat, lon });
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeLocation(lat, lon);
      setResult(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen bg-gray-950 text-white">
      <div className="flex-1 relative">
        <SearchBar onSelect={handleSelect} />
        <Map2D onMapClick={handleSelect} selectedCoords={coords} />
      </div>

      <div className="w-96 bg-gray-900 overflow-y-auto border-l border-gray-800">
        {loading && (
          <div className="p-8 text-center text-gray-400">
            <div className="animate-spin text-4xl mb-4">⚡</div>
            분석 중...
          </div>
        )}
        {error && <div className="p-6 text-red-400">오류: {error}</div>}
        {result && !loading && <AnalysisPanel result={result} />}
        {!result && !loading && !error && (
          <div className="p-8 text-center text-gray-500">
            <div className="text-5xl mb-4">📍</div>
            지도를 클릭하거나 주소를 검색해 입지를 분석하세요
          </div>
        )}
      </div>
    </div>
  );
}
