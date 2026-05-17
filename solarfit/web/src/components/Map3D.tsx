import { useEffect, useRef, useState } from 'react';

interface Props {
  lat: number;
  lon: number;
}

declare global {
  interface Window {
    vw: any;
    ws3d: any;
    Cesium: any;
  }
}

const CONTAINER_ID = 'vworld3d-container';

function flyCamera(viewer: any, lon: number, lat: number) {
  if (!viewer) return;
  try {
    // Use ellipsoid.cartographicToCartesian — avoids needing window.Cesium directly
    const ellipsoid = viewer.scene?.globe?.ellipsoid;
    if (!ellipsoid) return;
    const destination = ellipsoid.cartographicToCartesian({
      longitude: lon * Math.PI / 180,
      latitude: lat * Math.PI / 180,
      height: 2000,
    });
    viewer.camera.flyTo({
      destination,
      orientation: { heading: 0, pitch: -Math.PI / 4, roll: 0 },
      duration: 1.5,
    });
  } catch {
    // ignore camera errors
  }
}

export default function Map3D({ lat, lon }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [errorMsg, setErrorMsg] = useState('');

  // Camera update when coordinates change after map is ready
  useEffect(() => {
    if (viewerRef.current) {
      flyCamera(viewerRef.current, lon, lat);
    }
  }, [lat, lon]);

  // One-time initialization
  useEffect(() => {
    const key = import.meta.env.VITE_VWORLD_KEY ?? '';
    if (!key || key === 'your_vworld_key_here') {
      setStatus('error');
      setErrorMsg('VITE_VWORLD_KEY가 설정되지 않았습니다');
      return;
    }

    // If VWorld scripts already loaded from a previous mount, init directly
    if (window.ws3d?.initViewer) {
      initViewer(key, lon, lat);
      return;
    }

    // VWorld webglMapInit.js uses document.write() to inject sub-scripts.
    // Browsers block this from async scripts, so we collect URLs and replay serially.
    const originalWrite = document['write'].bind(document);
    const scriptQueue: string[] = [];
    document['write'] = (markup: string) => {
      const m = markup.match(/src=['"]([^'"]+)['"]/);
      if (m) scriptQueue.push(m[1]);
    };

    const domain = window.location.host || 'localhost';
    const script = document.createElement('script');
    script.src = `https://map.vworld.kr/js/webglMapInit.js.do?version=2.0&apiKey=${key}&domain=${domain}`;

    script.onerror = () => {
      document['write'] = originalWrite;
      setStatus('error');
      setErrorMsg('VWorld 스크립트 로드 실패 (네트워크 또는 API 키 오류)');
    };

    script.onload = async () => {
      document['write'] = originalWrite;

      // Load collected sub-scripts serially to preserve dependency order
      for (const src of scriptQueue) {
        await new Promise<void>(resolve => {
          const s = document.createElement('script');
          s.src = src;
          s.onload = s.onerror = () => resolve();
          document.head.appendChild(s);
        });
      }

      if (window.ws3d?.initViewer) {
        initViewer(key, lon, lat);
      } else {
        setStatus('error');
        setErrorMsg('VWorld 3D 로드 실패 — VWorld 콘솔에서 localhost:5174 도메인 등록 확인');
      }
    };

    document.head.appendChild(script);

    return () => {
      document['write'] = originalWrite;
      if (viewerRef.current?.destroy) {
        try { viewerRef.current.destroy(); } catch { /* ignore */ }
        viewerRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function initViewer(_key: string, lon: number, lat: number) {
    try {
      // Use ws3d (Cesium) directly — vw.Map wrapper has broken option handling
      const viewer = window.ws3d.initViewer('#' + CONTAINER_ID, true);
      viewerRef.current = viewer;
      flyCamera(viewer, lon, lat);
      setStatus('ready');
    } catch (e) {
      setStatus('error');
      setErrorMsg(`VWorld 3D 초기화 실패: ${(e as Error).message}`);
    }
  }

  return (
    <div className="w-full h-full relative">
      <div id={CONTAINER_ID} ref={containerRef} className="w-full h-full" />

      {status === 'loading' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 text-gray-400 pointer-events-none">
          <div className="text-4xl mb-4 animate-spin">⚡</div>
          <p className="text-sm">3D 지도 로딩 중...</p>
        </div>
      )}

      {status === 'error' && (
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
