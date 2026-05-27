import { useState } from 'react';
import type { AnalysisResult } from './types';
import { analyzeLocation } from './api';
import SearchBar from './components/SearchBar';
import Map2D from './components/Map2D';
import Map3D from './components/Map3D';
import AnalysisPanel from './components/AnalysisPanel';
import AppHeader from './components/AppHeader';
import SolarExplorePage from './components/SolarExplorePage';

type View = 'home' | 'explore';

function HomePage() {
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<'2d' | '3d'>('2d');

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
    <div className="flex min-h-0 flex-1 bg-gray-950 text-white">
      <div className="flex-1 relative">
        <SearchBar onSelect={handleSelect} />

        <div className="absolute top-4 right-4 z-[1000] flex bg-gray-900 rounded-lg overflow-hidden shadow-lg">
          <button
            onClick={() => setMode('2d')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${mode === '2d' ? 'bg-yellow-400 text-gray-900' : 'text-gray-300 hover:text-white'}`}
          >2D</button>
          <button
            onClick={() => setMode('3d')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${mode === '3d' ? 'bg-yellow-400 text-gray-900' : 'text-gray-300 hover:text-white'}`}
          >3D</button>
        </div>

        {mode === '2d'
          ? <Map2D onMapClick={handleSelect} selectedCoords={coords} />
          : coords
            ? <Map3D lat={coords.lat} lon={coords.lon} />
            : <div className="flex items-center justify-center h-full text-gray-500">먼저 위치를 선택하세요</div>
        }
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

export default function App() {
  const [view, setView] = useState<View>('home');

  return (
    <div className="flex h-screen flex-col bg-gray-950">
      <AppHeader activeView={view} onChange={setView} />
      {view === 'home' ? <HomePage /> : <SolarExplorePage />}
    </div>
  );
}
