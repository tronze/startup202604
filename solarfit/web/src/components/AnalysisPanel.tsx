import type { AnalysisResult } from '../types';
import ScoreGauge from './ScoreGauge';

interface Props {
  result: AnalysisResult;
}

function Row({
  label,
  value,
  unit = '',
  ok,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  ok?: boolean;
}) {
  const color =
    ok === true ? 'text-green-400' : ok === false ? 'text-red-400' : 'text-gray-200';
  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-800">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className={`text-sm font-medium ${color}`}>
        {value != null ? `${value}${unit}` : '—'}
      </span>
    </div>
  );
}

function RegFlag({ label, blocked }: { label: string; blocked: boolean }) {
  return (
    <div
      className={`flex items-center gap-2 text-xs px-2 py-1 rounded ${
        blocked ? 'bg-red-900/50 text-red-300' : 'bg-gray-800 text-gray-400'
      }`}
    >
      <span>{blocked ? '🔴' : '🟢'}</span>
      {label}
    </div>
  );
}

export default function AnalysisPanel({ result }: Props) {
  const { score, terrain, parcel, land_value, regulatory, substation, annual_ghi_kwh } = result;

  // 토지이음: 토지이용계획 + 개발 제한 확인 (PNU 직접 조회 지원)
  const registryUrl = parcel.pnu
    ? `https://www.eum.go.kr/web/ar/lu/luLandDet.do?pnu=${parcel.pnu}`
    : null;

  return (
    <div className="p-4">
      {score && (
        <ScoreGauge
          score={score.total}
          grade={score.grade}
          passed={score.passed_hard_filter}
        />
      )}

      <section className="mb-4">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-2">필지 정보</h3>
        <Row label="지목" value={parcel.jimok_name ?? parcel.jimok} />
        <Row label="면적" value={parcel.area_m2?.toLocaleString()} unit=" m²" />
        <Row label="소유구분" value={land_value.ownership_type} />
        <Row label="공시지가" value={land_value.official_price_per_m2?.toLocaleString()} unit=" 원/m²" />
        {parcel.address && <div className="text-xs text-gray-500 pt-2">{parcel.address}</div>}
      </section>

      <section className="mb-4">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-2">입지 조건</h3>
        <Row
          label="연간 일사량"
          value={annual_ghi_kwh?.toFixed(0)}
          unit=" kWh/m²/yr"
          ok={annual_ghi_kwh != null ? annual_ghi_kwh >= 1350 : undefined}
        />
        <Row label="해발고도" value={terrain.elevation_m?.toFixed(0)} unit=" m" />
        <Row
          label="경사도"
          value={terrain.slope_deg?.toFixed(1)}
          unit="°"
          ok={terrain.slope_deg != null ? terrain.slope_deg < 15 : undefined}
        />
        <Row
          label="방위"
          value={
            terrain.is_south_facing != null
              ? terrain.is_south_facing
                ? '남향'
                : '북향'
              : null
          }
          ok={terrain.is_south_facing ?? undefined}
        />
        <Row label="변전소" value={substation.name} />
        <Row
          label="변전소 거리"
          value={substation.distance_km?.toFixed(1)}
          unit=" km"
          ok={substation.distance_km != null ? substation.distance_km < 5 : undefined}
        />
      </section>

      <section className="mb-4">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-2">규제 현황</h3>
        <div className="flex flex-wrap gap-1">
          <RegFlag label="농업진흥" blocked={regulatory.agri_promotion} />
          <RegFlag label="자연보전" blocked={regulatory.natural_conservation} />
          <RegFlag label="습지보호" blocked={regulatory.wetland_protection} />
          <RegFlag label="산림보호" blocked={regulatory.forest_protection} />
          <RegFlag label="그린벨트" blocked={regulatory.greenbelt} />
          <RegFlag label="상수원" blocked={regulatory.water_source} />
          <RegFlag label="급경사위험" blocked={regulatory.steep_slope_hazard} />
          <RegFlag label="재해위험" blocked={regulatory.disaster_risk} />
        </div>
      </section>

      {registryUrl && (
        <a
          href={registryUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full text-center py-2 bg-yellow-400 text-gray-900 font-bold rounded-lg hover:bg-yellow-300 text-sm"
        >
          📋 토지이음 (이용계획·규제 상세)
        </a>
      )}
    </div>
  );
}
