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
    $: any;
    jQuery: any;
    __vworld3dLoader?: Promise<void>;
  }
}

const CONTAINER_ID = 'vworld3d-container';

function toCameraPosition(lon: number, lat: number, height = 2000) {
  if (!window.vw?.CameraPosition || !window.vw?.CoordZ || !window.vw?.Direction) {
    return null;
  }

  return new window.vw.CameraPosition(
    new window.vw.CoordZ(lon, lat, height),
    new window.vw.Direction(0, -80, 0),
  );
}

function moveCamera(map: any, lon: number, lat: number) {
  if (!map) return;
  try {
    const position = toCameraPosition(lon, lat);
    if (position) {
      map.moveTo?.(position);
    }
  } catch {
    // ignore camera errors
  }
}

function loadScript(src: string) {
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`);
    if (existing) {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`스크립트 로드 실패: ${src}`));
    document.head.appendChild(script);
  });
}

async function loadJQuery() {
  if (window.$ && window.jQuery) {
    return;
  }

  await loadScript('https://code.jquery.com/jquery-3.7.1.min.js');
}

function loadVWorld3D(key: string) {
  if (window.vw?.Map) {
    return Promise.resolve();
  }

  if (window.__vworld3dLoader) {
    return window.__vworld3dLoader;
  }

  window.__vworld3dLoader = new Promise<void>((resolve, reject) => {
    const originalWrite = document.write.bind(document);
    const scriptQueue: string[] = [];

    document.write = (markup: string) => {
      const matches = markup.matchAll(/<script[^>]+src=["']([^"']+)["'][^>]*>/gi);
      for (const match of matches) {
        scriptQueue.push(new URL(match[1], 'https://map.vworld.kr').href);
      }
    };

    const restoreWrite = () => {
      document.write = originalWrite;
    };

    const scriptSrc = `https://map.vworld.kr/js/webglMapInit.js.do?version=3.0&apiKey=${encodeURIComponent(key)}`;
    const script = document.createElement('script');
    script.src = scriptSrc;

    script.onerror = () => {
      restoreWrite();
      window.__vworld3dLoader = undefined;
      reject(new Error('VWorld 스크립트 로드 실패 (네트워크 또는 API 키 오류)'));
    };

    script.onload = async () => {
      restoreWrite();

      try {
        for (const src of scriptQueue) {
          await loadScript(src);
        }

        if (window.vw?.Map) {
          resolve();
        } else {
          window.__vworld3dLoader = undefined;
          reject(new Error('VWorld 3D API가 초기화되지 않았습니다'));
        }
      } catch (error) {
        window.__vworld3dLoader = undefined;
        reject(error);
      }
    };

    loadJQuery()
      .then(() => {
        document.head.appendChild(script);
      })
      .catch((error: Error) => {
        restoreWrite();
        window.__vworld3dLoader = undefined;
        reject(error);
      });
  });

  return window.__vworld3dLoader;
}

export default function Map3D({ lat, lon }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [errorMsg, setErrorMsg] = useState('');

  // Camera update when coordinates change after map is ready
  useEffect(() => {
    if (mapRef.current) {
      moveCamera(mapRef.current, lon, lat);
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

    let cancelled = false;

    loadVWorld3D(key)
      .then(() => {
        if (!cancelled) {
          initMap(lon, lat);
        }
      })
      .catch((error: Error) => {
        if (!cancelled) {
          setStatus('error');
          setErrorMsg(error.message);
        }
      });

    return () => {
      cancelled = true;
      if (mapRef.current?.destroy) {
        try { mapRef.current.destroy(); } catch { /* ignore */ }
      }
      mapRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function initMap(lon: number, lat: number) {
    if (!containerRef.current || !window.vw?.Map) {
      setStatus('error');
      setErrorMsg('VWorld 3D 컨테이너를 찾을 수 없습니다');
      return;
    }

    try {
      const initialPosition = toCameraPosition(lon, lat);
      const map = new window.vw.Map();

      map.setOption({
        mapId: CONTAINER_ID,
        initPosition: initialPosition,
        logo: false,
        navigation: true,
      });
      map.setMapId(CONTAINER_ID);
      if (initialPosition) {
        map.setInitPosition(initialPosition);
      }
      map.setLogoVisible?.(false);
      map.setNavigationZoomVisible?.(false);
      map.start();

      mapRef.current = map;
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
