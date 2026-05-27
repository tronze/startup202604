import type { IndustrialArea } from '../types';
import { regions } from '../data/industrialAreas';

interface Props {
  areas: IndustrialArea[];
  selectedId: string;
  selectedRegion: string;
  onRegionChange: (region: string) => void;
  onSelect: (area: IndustrialArea) => void;
}

export default function IndustrialAreaList({
  areas,
  selectedId,
  selectedRegion,
  onRegionChange,
  onSelect,
}: Props) {
  return (
    <aside className="z-10 flex h-64 w-full shrink-0 flex-col border-b border-gray-800 bg-gray-950/95 text-white lg:h-full lg:w-80 lg:border-b-0 lg:border-r">
      <div className="border-b border-gray-800 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-yellow-300">Factory Areas</p>
        <h2 className="mt-1 text-lg font-semibold">새로 모색할 지역</h2>
        <p className="mt-2 text-xs leading-5 text-gray-400">
          산업단지를 선택하면 3D 지도 이동, 일조량 히트맵, 예상 발전량 분석이 함께 갱신됩니다.
        </p>
      </div>

      <div className="border-b border-gray-800 p-3">
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => onRegionChange('전체')}
            className={`rounded px-2.5 py-1.5 text-xs ${
              selectedRegion === '전체' ? 'bg-yellow-400 text-gray-950' : 'bg-gray-900 text-gray-300'
            }`}
          >
            전체
          </button>
          {regions.map((region) => (
            <button
              key={region}
              onClick={() => onRegionChange(region)}
              className={`rounded px-2.5 py-1.5 text-xs ${
                selectedRegion === region ? 'bg-yellow-400 text-gray-950' : 'bg-gray-900 text-gray-300'
              }`}
            >
              {region}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <div className="space-y-2">
          {areas.map((area) => (
            <button
              key={area.id}
              onClick={() => onSelect(area)}
              className={`w-full rounded border p-3 text-left transition-colors ${
                selectedId === area.id
                  ? 'border-yellow-300 bg-yellow-300/10'
                  : 'border-gray-800 bg-gray-900/80 hover:border-gray-700 hover:bg-gray-900'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-gray-100">{area.name}</div>
                  <div className="mt-1 text-xs text-gray-500">
                    {area.region} {area.city} · {area.type}
                  </div>
                </div>
                <span className="rounded bg-gray-800 px-2 py-1 text-[11px] text-yellow-200">
                  {area.ghiKwhM2Year}
                </span>
              </div>
              <div className="mt-3 flex gap-1.5">
                {area.industries.slice(0, 3).map((industry) => (
                  <span key={industry} className="rounded bg-gray-800 px-2 py-1 text-[11px] text-gray-300">
                    {industry}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
