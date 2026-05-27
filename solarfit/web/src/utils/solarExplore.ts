import type { IndustrialArea, IndustrialAreaAnalysis } from '../types';

const SMP_KRW_KWH = 92;
const REC_KRW_KWH = 63;
const INSTALL_COST_KRW_PER_MW = 1_120_000_000;
const PERFORMANCE_RATIO = 0.79;
const CO2_TON_PER_MWH = 0.459;
const ROOFTOP_MW_PER_M2 = 0.00012;

export function analyzeIndustrialArea(area: IndustrialArea): IndustrialAreaAnalysis {
  const solarFactors = estimateSolarSurfaceFactors(area, area.boundary);
  const capacityMw = area.recommendedCapacityMw;
  const annualGenerationMwh = capacityMw * solarFactors.effectivePvoutKwhKwpYear;
  const annualRevenueKrw = annualGenerationMwh * 1000 * (SMP_KRW_KWH + REC_KRW_KWH);
  const installCostKrw = capacityMw * INSTALL_COST_KRW_PER_MW;
  const paybackYears = installCostKrw / annualRevenueKrw;
  const co2ReductionTon = annualGenerationMwh * CO2_TON_PER_MWH;

  return {
    capacityMw,
    annualGenerationMwh,
    annualRevenueKrw,
    installCostKrw,
    paybackYears,
    co2ReductionTon,
    smpKrwKwh: SMP_KRW_KWH,
    recKrwKwh: REC_KRW_KWH,
    performanceRatio: PERFORMANCE_RATIO,
    ...solarFactors,
  };
}

function toMeterPoints(boundary: [number, number][]) {
  if (boundary.length === 0) return [];
  const meanLat = boundary.reduce((sum, point) => sum + point[1], 0) / boundary.length;
  const metersPerLat = 111_320;
  const metersPerLon = metersPerLat * Math.cos((meanLat * Math.PI) / 180);
  const origin = boundary[0];

  return boundary.map(([lon, lat]) => [
    (lon - origin[0]) * metersPerLon,
    (lat - origin[1]) * metersPerLat,
  ]);
}

export function polygonAreaM2(boundary: [number, number][]) {
  if (boundary.length < 3) return 0;

  const points = toMeterPoints(boundary);

  const twiceArea = points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length];
    return sum + point[0] * next[1] - next[0] * point[1];
  }, 0);

  return Math.abs(twiceArea) / 2;
}

function polygonPerimeterM(boundary: [number, number][]) {
  const points = toMeterPoints(boundary);
  return points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length];
    return sum + Math.hypot(next[0] - point[0], next[1] - point[1]);
  }, 0);
}

function longestEdgeEastWestScore(boundary: [number, number][]) {
  const points = toMeterPoints(boundary);
  let longest = 0;
  let bestAngleFromEast = 45;

  points.forEach((point, index) => {
    const next = points[(index + 1) % points.length];
    const dx = next[0] - point[0];
    const dy = next[1] - point[1];
    const length = Math.hypot(dx, dy);
    if (length > longest) {
      longest = length;
      bestAngleFromEast = Math.abs((Math.atan2(dy, dx) * 180) / Math.PI);
      if (bestAngleFromEast > 90) bestAngleFromEast = 180 - bestAngleFromEast;
    }
  });

  return Math.max(0, Math.min(1, 1 - bestAngleFromEast / 90));
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function estimateSolarSurfaceFactors(area: IndustrialArea, boundary: [number, number][]) {
  if (area.effectiveGhiKwhM2Year != null
    && area.shadingLossPct != null
    && area.incidenceAdjustmentPct != null
    && area.shapeEfficiencyPct != null
  ) {
    return {
      effectivePvoutKwhKwpYear: area.pvoutKwhKwpYear,
      effectiveGhiKwhM2Year: area.effectiveGhiKwhM2Year,
      shadingLossPct: area.shadingLossPct,
      incidenceAdjustmentPct: area.incidenceAdjustmentPct,
      shapeEfficiencyPct: area.shapeEfficiencyPct,
    };
  }

  const selectedAreaM2 = polygonAreaM2(boundary);
  const perimeterM = polygonPerimeterM(boundary);
  const compactness = selectedAreaM2 > 0 && perimeterM > 0
    ? clamp((4 * Math.PI * selectedAreaM2) / (perimeterM ** 2), 0, 1)
    : 0.7;
  const roofDensity = selectedAreaM2 > 0
    ? clamp(area.availableRoofM2 / selectedAreaM2, 0.08, 0.85)
    : 0.35;
  const eastWestScore = longestEdgeEastWestScore(boundary);

  const shapeEfficiencyPct = clamp(82 + compactness * 16, 82, 98);
  const shadingLossPct = clamp(4 + roofDensity * 7 + (1 - compactness) * 7, 4, 18);
  const incidenceAdjustmentPct = clamp((eastWestScore - 0.5) * 5, -2.5, 2.5);
  const basePvout = area.basePvoutKwhKwpYear ?? area.pvoutKwhKwpYear;
  const effectivePvoutKwhKwpYear = basePvout
    * (1 - shadingLossPct / 100)
    * (1 + incidenceAdjustmentPct / 100);
  const effectiveGhiKwhM2Year = area.ghiKwhM2Year
    * (1 - shadingLossPct / 100)
    * (1 + incidenceAdjustmentPct / 100);

  return {
    effectivePvoutKwhKwpYear,
    effectiveGhiKwhM2Year,
    shadingLossPct,
    incidenceAdjustmentPct,
    shapeEfficiencyPct,
  };
}

export function createAdjustedIndustrialArea(
  baseArea: IndustrialArea,
  boundary: [number, number][] | null
): IndustrialArea {
  if (!boundary) return baseArea;

  const selectedAreaM2 = polygonAreaM2(boundary);
  const originalAreaM2 = polygonAreaM2(baseArea.boundary);
  const areaRatio = originalAreaM2 > 0 ? selectedAreaM2 / originalAreaM2 : 1;
  const availableRoofM2 = Math.max(
    5_000,
    Math.round(baseArea.availableRoofM2 * areaRatio)
  );
  const adjustedArea = {
    ...baseArea,
    boundary,
    lat: boundary.reduce((sum, point) => sum + point[1], 0) / boundary.length,
    lon: boundary.reduce((sum, point) => sum + point[0], 0) / boundary.length,
    availableRoofM2,
    recommendedCapacityMw: Number((availableRoofM2 * ROOFTOP_MW_PER_M2).toFixed(1)),
    selectedAreaM2,
    isCustomSelection: true,
    basePvoutKwhKwpYear: baseArea.basePvoutKwhKwpYear ?? baseArea.pvoutKwhKwpYear,
  };
  const factors = estimateSolarSurfaceFactors(adjustedArea, boundary);

  return {
    ...adjustedArea,
    pvoutKwhKwpYear: Number(factors.effectivePvoutKwhKwpYear.toFixed(0)),
    effectiveGhiKwhM2Year: Number(factors.effectiveGhiKwhM2Year.toFixed(0)),
    shadingLossPct: Number(factors.shadingLossPct.toFixed(1)),
    incidenceAdjustmentPct: Number(factors.incidenceAdjustmentPct.toFixed(1)),
    shapeEfficiencyPct: Number(factors.shapeEfficiencyPct.toFixed(0)),
  };
}

export function formatKrw(value: number) {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}억 원`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(0)}만 원`;
  return `${value.toLocaleString()}원`;
}
