import { useEffect, useRef } from 'react';
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

// vw.Map은 전역 상태를 readonly로 등록하므로 딱 한 번만 생성해야 함.
// 모듈 레벨 싱글톤으로 유지하고, 컴포넌트는 container 첨부/분리만 담당.
let _singleton: { map: any; container: HTMLDivElement } | null = null;

function getOrCreateMap(lon: number, lat: number): { map: any; container: HTMLDivElement } | null {
  if (_singleton) return _singleton;
  if (!window.vw?.Map) return null;

  const container = document.createElement('div');
  container.style.cssText = 'width:100%;height:100%';
  container.id = 'vworld3d-singleton';

  try {
    const pos = window.vw.CameraPosition
      ? new window.vw.CameraPosition(new window.vw.CoordZ(lon, lat, 500), new window.vw.Direction(0, -80, 0))
      : null;

    const map = new window.vw.Map();
    map.setOption({ mapId: container.id, initPosition: pos, logo: false, navigation: true });
    map.setMapId(container.id);
    if (pos) map.setInitPosition(pos);
    map.setLogoVisible?.(false);
    map.setNavigationZoomVisible?.(false);
    map.start();

    _singleton = { map, container };
    return _singleton;
  } catch (e) {
    console.error('VWorld 3D 초기화 실패:', e);
    return null;
  }
}

export default function Map3D({ lat, lon }: Props) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const loaderState = useVWorldLoader();

  // 스크립트 로드 완료 시 map 싱글톤 생성 후 wrapper에 붙임
  useEffect(() => {
    if (loaderState !== 'ready' || !wrapperRef.current) return;

    const singleton = getOrCreateMap(lon, lat);
    if (!singleton) return;

    wrapperRef.current.appendChild(singleton.container);

    return () => {
      // 파괴하지 않고 detach만 — 다음 마운트에서 재사용
      singleton.container.remove();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaderState]);

  // 좌표 변경 시 카메라 이동
  useEffect(() => {
    if (!_singleton?.map || !window.vw?.CameraPosition) return;
    try {
      const pos = new window.vw.CameraPosition(
        new window.vw.CoordZ(lon, lat, 500),
        new window.vw.Direction(0, -80, 0)
      );
      _singleton.map.moveTo?.(pos);
    } catch { /* ignore */ }
  }, [lat, lon]);

  const isError = typeof loaderState === 'object';
  const errorMsg = isError ? loaderState.error : '';
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
