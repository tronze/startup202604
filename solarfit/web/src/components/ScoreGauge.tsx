interface Props {
  score: number;
  grade: string;
  passed: boolean;
}

const gradeColor: Record<string, string> = {
  A: '#22c55e',
  B: '#86efac',
  C: '#fbbf24',
  D: '#f97316',
  F: '#ef4444',
};

export default function ScoreGauge({ score, grade, passed }: Props) {
  const color = gradeColor[grade] ?? '#6b7280';
  const r = 45;
  const circumference = 2 * Math.PI * r;
  const dashOffset = circumference * (1 - score / 100);

  return (
    <div className="flex flex-col items-center py-6">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#1f2937" strokeWidth="10" />
        <circle
          cx="60" cy="60" r={r}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform="rotate(-90 60 60)"
          style={{ transition: 'stroke-dashoffset 0.5s ease' }}
        />
        <text x="60" y="56" textAnchor="middle" fill="white" fontSize="24" fontWeight="bold">
          {score}
        </text>
        <text x="60" y="74" textAnchor="middle" fill={color} fontSize="14" fontWeight="bold">
          {grade}등급
        </text>
      </svg>
      {!passed && (
        <span className="mt-2 text-xs text-red-400 bg-red-900/40 px-2 py-1 rounded">
          규제구역 해당 — 개발 제한
        </span>
      )}
    </div>
  );
}
