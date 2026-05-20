import { useEffect, useRef, useState } from 'react';
import { useVWorldLoader } from '../hooks/useVWorldLoader';

interface Props {
  lat: number;
  lon: number;
}

declare global {
  interface Window {
    vw: any;
  }
}

function makePosition(lon: number, lat: number) {
  if (!window.vw?.CameraPosition) return null;
  try {
    return new window.vw.CameraPosition(
      new window.vw.CoordZ(lon, lat, 500),
      new window.vw.Direction(0, -80, 0)
    );
  } catch {
    return null;
  }
}

export default function Map3D({ lat, lon }: Props) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const loaderState = useVWorldLoader();

  // Initialize map when VWorld scripts are ready
  useEffect(() => {
    if (loaderState !== 'ready' || !wrapperRef.current) return;

    // Create a fresh container div each time this effect runs.
    // This is the key fix: JSX에 div를 두면 StrictMode 재실행 시 같은 DOM 노드에
    // vw.Map이 두 번 초기화되어 readonly 에러가 발생함.
    const container = document.createElement('div');
    container.style.cssText = 'width:100%;height:100%';
    container.id = `vworld3d-${Math.random().toString(36).slice(2)}`;
    wrapperRef.current.appendChild(container);

    try {
      const pos = makePosition(lon, lat);
      const map = new window.vw.Map();
      map.setOption({ mapId: container.id, initPosition: pos, logo: false, navigation: true });
      map.setMapId(container.id);
      if (pos) map.setInitPosition(pos);
      map.setLogoVisible?.(false);
      map.setNavigationZoomVisible?.(false);
      map.start();
      mapRef.current = map;
    } catch (e) {
      setMapError((e as Error).message);
      container.remove();
    }

    return () => {
      if (mapRef.current?.destroy) {
        try { mapRef.current.destroy(); } catch { /* ignore */ }
        mapRef.current = null;
      }
      container.remove();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaderState]);

  // Move camera when coordinates change
  useEffect(() => {
    if (!mapRef.current) return;
    const pos = makePosition(lon, lat);
    if (pos) try { mapRef.current.moveTo?.(pos); } catch { /* ignore */ }
  }, [lat, lon]);

  const isError = !!mapError || typeof loaderState === 'object';
  const errorMsg = mapError ?? (typeof loaderState === 'object' ? loaderState.error : '');
  const isLoading = !isError && loaderState !== 'ready';

  return (
    <div className="w-full h-full relative">
      <div ref={wrapperRef} className="w-full h-full" />

      {isLoading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 text-gray-400 pointer-events-none">
          <div className="text-4xl mb-4 animate-spin">⚡</div>
          <p className="text-sm">3D 지도 로딩 중...</p>
        </div>
      )}

      {isError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 text-gray-400">
          <div className="text-4xl mb-4">🌏</div>
          <p className="text-sm text-center px-8 text-red-400">{errorMsg}</p>
          <p className="text-xs text-gray-600 mt-2 text-center px-8">
            VWorld 3D는 등록된 도메인에서만 작동합니다.<br />
            운영 환경에서 도메인을 API 키에 등록하세요.
          </p>
        </div>
      )}
    </div>
  );
}
