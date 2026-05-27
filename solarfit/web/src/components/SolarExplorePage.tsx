import { useMemo, useState } from 'react';
import { industrialAreas } from '../data/industrialAreas';
import type { IndustrialArea } from '../types';
import { createAdjustedIndustrialArea } from '../utils/solarExplore';
import Map3D from './Map3D';
import IndustrialAreaList from './IndustrialAreaList';
import ExploreAnalysisPanel from './ExploreAnalysisPanel';

export default function SolarExplorePage() {
  const [selectedArea, setSelectedArea] = useState<IndustrialArea>(industrialAreas[0]);
  const [selectedRegion, setSelectedRegion] = useState('전체');
  const [customBoundary, setCustomBoundary] = useState<[number, number][] | null>(null);

  const visibleAreas = useMemo(() => {
    if (selectedRegion === '전체') return industrialAreas;
    return industrialAreas.filter((area) => area.region === selectedRegion);
  }, [selectedRegion]);

  const analysisArea = useMemo(
    () => createAdjustedIndustrialArea(selectedArea, customBoundary),
    [selectedArea, customBoundary]
  );

  const mapAreas = useMemo(
    () => visibleAreas.map((area) => area.id === analysisArea.id ? analysisArea : area),
    [analysisArea, visibleAreas]
  );

  function handleRegionChange(region: string) {
    setSelectedRegion(region);
    setCustomBoundary(null);
    const nextArea = region === '전체'
      ? industrialAreas[0]
      : industrialAreas.find((area) => area.region === region);
    if (nextArea) setSelectedArea(nextArea);
  }

  function handleAreaSelect(area: IndustrialArea) {
    setSelectedArea(area);
    setCustomBoundary(null);
    if (selectedRegion !== '전체' && selectedRegion !== area.region) {
      setSelectedRegion(area.region);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-gray-950 lg:flex-row">
      <IndustrialAreaList
        areas={visibleAreas}
        selectedId={analysisArea.id}
        selectedRegion={selectedRegion}
        onRegionChange={handleRegionChange}
        onSelect={handleAreaSelect}
      />

      <main className="relative min-h-[420px] min-w-0 flex-1">
        <Map3D
          lat={selectedArea.lat}
          lon={selectedArea.lon}
          areas={mapAreas}
          selectedArea={analysisArea}
          onAreaSelect={handleAreaSelect}
          onAreaBoundaryChange={setCustomBoundary}
        />
        <div className="pointer-events-none absolute left-4 top-4 z-10 rounded border border-gray-800 bg-gray-950/85 px-3 py-2 text-xs text-gray-300 shadow-lg">
          <span className="font-semibold text-yellow-200">VWorld 3D</span>
          <span className="ml-2 text-gray-500">영역 이동 · 꼭지점 편집 · 실시간 분석</span>
        </div>
        <div className="pointer-events-none absolute bottom-4 left-4 z-10 flex items-center gap-2 rounded border border-gray-800 bg-gray-950/85 px-3 py-2 text-[11px] text-gray-300">
          <span className="h-2 w-10 rounded bg-gradient-to-r from-sky-400 via-yellow-300 to-red-500" />
          낮음 · 연간 GHI · 높음
        </div>
      </main>

      <ExploreAnalysisPanel area={analysisArea} />
    </div>
  );
}
