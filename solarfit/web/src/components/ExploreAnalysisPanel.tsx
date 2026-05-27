import type { IndustrialArea } from '../types';
import { analyzeIndustrialArea, formatKrw } from '../utils/solarExplore';

interface Props {
  area: IndustrialArea;
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded border border-gray-800 bg-gray-900 p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 text-lg font-semibold text-white">{value}</div>
      {sub && <div className="mt-1 text-[11px] text-gray-500">{sub}</div>}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-gray-800 py-2 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-right font-medium text-gray-100">{value}</span>
    </div>
  );
}

export default function ExploreAnalysisPanel({ area }: Props) {
  const analysis = analyzeIndustrialArea(area);

  return (
    <aside className="z-10 flex h-80 w-full shrink-0 flex-col border-t border-gray-800 bg-gray-950/95 text-white lg:h-full lg:w-96 lg:border-l lg:border-t-0">
      <div className="border-b border-gray-800 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-yellow-300">Solar Feasibility</p>
        <h2 className="mt-1 text-lg font-semibold">{area.name}</h2>
        <p className="mt-2 text-xs leading-5 text-gray-400">
          {area.isCustomSelection
            ? '사용자가 조정한 선택 영역을 기준으로 발전량과 수입을 재계산했습니다.'
            : area.landUseNote}
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="grid grid-cols-2 gap-2">
          <Metric
            label="예상 연 발전량"
            value={`${analysis.annualGenerationMwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} MWh`}
            sub={`${analysis.effectivePvoutKwhKwpYear.toFixed(0)} kWh/kWp·yr`}
          />
          <Metric
            label="예상 연 수입"
            value={formatKrw(analysis.annualRevenueKrw)}
            sub={`SMP+REC ${analysis.smpKrwKwh + analysis.recKrwKwh}원/kWh`}
          />
          <Metric
            label="권장 설치용량"
            value={`${analysis.capacityMw.toFixed(1)} MW`}
            sub={`${area.availableRoofM2.toLocaleString()} m² 설치 후보`}
          />
          <Metric
            label="투자 회수"
            value={`${analysis.paybackYears.toFixed(1)}년`}
            sub={formatKrw(analysis.installCostKrw)}
          />
        </div>

        <section className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">지역 조건</h3>
          <div className="mt-2">
            <Row label="연간 일조량/GHI" value={`${area.ghiKwhM2Year.toLocaleString()} kWh/m²·yr`} />
            <Row label="보정 일사량" value={`${analysis.effectiveGhiKwhM2Year.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh/m²·yr`} />
            <Row label="그림자 손실" value={`${analysis.shadingLossPct.toFixed(1)}%`} />
            <Row
              label="입사 보정"
              value={`${analysis.incidenceAdjustmentPct > 0 ? '+' : ''}${analysis.incidenceAdjustmentPct.toFixed(1)}%`}
            />
            <Row label="도형 효율" value={`${analysis.shapeEfficiencyPct.toFixed(0)}%`} />
            {area.selectedAreaM2 && (
              <Row label="선택 영역 면적" value={`${area.selectedAreaM2.toLocaleString(undefined, { maximumFractionDigits: 0 })} m²`} />
            )}
            <Row label="계통 접근 거리" value={`${area.gridDistanceKm.toFixed(1)} km`} />
            <Row label="성능비 가정" value={`${Math.round(analysis.performanceRatio * 100)}%`} />
            <Row label="CO₂ 절감 추정" value={`${analysis.co2ReductionTon.toLocaleString(undefined, { maximumFractionDigits: 0 })} tCO₂/yr`} />
          </div>
        </section>

        <section className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">산업 구성</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {area.industries.map((industry) => (
              <span key={industry} className="rounded bg-gray-900 px-2.5 py-1.5 text-xs text-gray-200">
                {industry}
              </span>
            ))}
          </div>
        </section>

        <div className="mt-5 rounded border border-yellow-500/30 bg-yellow-500/10 p-3 text-xs leading-5 text-yellow-100">
          현재 수익은 SMP 92원/kWh, REC 환산 63원/kWh, MW당 설치비 11.2억 원을 둔 1차 추정입니다.
          그림자와 입사량은 선택 도형의 형태, 장축 방향, 설치 후보 밀도를 이용한 예비 보정값입니다.
        </div>
      </div>
    </aside>
  );
}
