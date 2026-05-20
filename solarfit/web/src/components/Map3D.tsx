import { useEffect, useRef } from 'react';

interface Props {
  lat: number;
  lon: number;
}

const KEY = import.meta.env.VITE_VWORLD_KEY ?? '';

export default function Map3D({ lat, lon }: Props) {
  const iframeRef  = useRef<HTMLIFrameElement>(null);
  const readyRef   = useRef(false);          // iframe 내 VWorld 준비 완료 여부
  const pendingRef = useRef<{ lat: number; lon: number } | null>(null); // 준비 전 수신된 좌표

  /* ── iframe 메시지 수신 ── */
  useEffect(() => {
    function onMessage(e: MessageEvent) {
      // 우리 iframe에서 온 메시지만 처리
      if (e.source !== iframeRef.current?.contentWindow) return;
      if (e.data?.type !== 'vworld3d:ready') return;

      readyRef.current = true;

      // 준비되기 전에 받은 좌표가 있으면 지금 적용
      if (pendingRef.current) {
        iframeRef.current?.contentWindow?.postMessage(
          { type: 'flyTo', ...pendingRef.current }, '*'
        );
        pendingRef.current = null;
      }
    }
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  /* ── 좌표 변경 시 카메라 이동 ── */
  useEffect(() => {
    if (readyRef.current) {
      iframeRef.current?.contentWindow?.postMessage({ type: 'flyTo', lat, lon }, '*');
    } else {
      // 아직 ready 아님 → 큐에 저장, ready 시 위의 onMessage에서 적용
      pendingRef.current = { lat, lon };
    }
  }, [lat, lon]);

  if (!KEY || KEY === 'your_vworld_key_here') {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900 text-red-400 text-sm">
        VITE_VWORLD_KEY가 설정되지 않았습니다
      </div>
    );
  }

  // src에 lat/lon 포함: 마운트 시점의 좌표로 초기화. 이후 좌표 변경은 postMessage.
  // lat/lon이 src에 반영되면 iframe 리로드되므로, useMemo 없이 최초 1회만 계산.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const src = useRef(
    `/vworld3d.html?key=${encodeURIComponent(KEY)}&lat=${lat}&lon=${lon}`
  ).current;

  return (
    <iframe
      ref={iframeRef}
      src={src}
      className="w-full h-full border-0"
      title="VWorld 3D"
    />
  );
}
