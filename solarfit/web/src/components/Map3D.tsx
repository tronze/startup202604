import { useCallback, useEffect, useRef, useState } from 'react';
import type { IndustrialArea } from '../types';

interface Props {
  lat: number;
  lon: number;
  areas?: IndustrialArea[];
  selectedArea?: IndustrialArea;
  onAreaSelect?: (area: IndustrialArea) => void;
  onAreaBoundaryChange?: (boundary: [number, number][]) => void;
}

const KEY = import.meta.env.VITE_VWORLD_KEY ?? '';

export default function Map3D({
  lat,
  lon,
  areas = [],
  selectedArea,
  onAreaSelect,
  onAreaBoundaryChange,
}: Props) {
  const iframeRef  = useRef<HTMLIFrameElement>(null);
  const readyRef   = useRef(false);          // iframe 내 VWorld 준비 완료 여부
  const pendingRef = useRef<{ lat: number; lon: number } | null>(null); // 준비 전 수신된 좌표
  const areasRef = useRef<IndustrialArea[]>(areas);
  const [src] = useState(
    () => `/vworld3d.html?key=${encodeURIComponent(KEY)}&lat=${lat}&lon=${lon}`
  );

  useEffect(() => {
    areasRef.current = areas;
  }, [areas]);

  const postOverlay = useCallback(() => {
    iframeRef.current?.contentWindow?.postMessage({
      type: 'renderIndustrialAreas',
      areas,
      selectedAreaId: selectedArea?.id ?? null,
    }, '*');
  }, [areas, selectedArea?.id]);

  /* ── iframe 메시지 수신 ── */
  useEffect(() => {
    function onMessage(e: MessageEvent) {
      // 우리 iframe에서 온 메시지만 처리
      if (e.source !== iframeRef.current?.contentWindow) return;
      if (e.data?.type === 'vworld3d:areaSelected') {
        const area = areasRef.current.find((item) => item.id === e.data.areaId);
        if (area) onAreaSelect?.(area);
        return;
      }
      if (e.data?.type === 'vworld3d:areaBoundaryChanged') {
        onAreaBoundaryChange?.(e.data.boundary);
        return;
      }
      if (e.data?.type !== 'vworld3d:ready') return;

      readyRef.current = true;

      // 준비되기 전에 받은 좌표가 있으면 지금 적용
      if (pendingRef.current) {
        iframeRef.current?.contentWindow?.postMessage(
          { type: 'flyTo', ...pendingRef.current }, '*'
        );
        pendingRef.current = null;
      }
      postOverlay();
    }
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [onAreaBoundaryChange, onAreaSelect, postOverlay]);

  /* ── 좌표 변경 시 카메라 이동 ── */
  useEffect(() => {
    if (readyRef.current) {
      iframeRef.current?.contentWindow?.postMessage({ type: 'flyTo', lat, lon }, '*');
    } else {
      // 아직 ready 아님 → 큐에 저장, ready 시 위의 onMessage에서 적용
      pendingRef.current = { lat, lon };
    }
  }, [lat, lon]);

  useEffect(() => {
    if (readyRef.current) postOverlay();
  }, [postOverlay]);

  if (!KEY || KEY === 'your_vworld_key_here') {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900 text-red-400 text-sm">
        VITE_VWORLD_KEY가 설정되지 않았습니다
      </div>
    );
  }

  return (
    <iframe
      ref={iframeRef}
      src={src}
      className="w-full h-full border-0"
      title="VWorld 3D"
    />
  );
}
