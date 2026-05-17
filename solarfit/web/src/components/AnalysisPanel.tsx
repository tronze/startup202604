import type { AnalysisResult } from '../types';

interface Props { result: AnalysisResult; }

export default function AnalysisPanel({ result: _result }: Props) {
  return <div data-testid="analysis-panel" />;
}
