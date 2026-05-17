import { useEffect, useRef, useState } from 'react';

interface Props {
  lat: number;
  lon: number;
}

declare global {
  interface Window {
    vw: any;
    Cesium: any;
  }
}

const CONTAINER_ID = 'vworld3d-container';

export default function Map3D({ lat, lon }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const key = import.meta.env.VITE_VWORLD_KEY ?? '';
    if (!key || key === 'your_vworld_key_here') {
      setStatus('error');
      setErrorMsg('VITE_VWORLD_KEY가 설정되지 않았습니다');
      return;
    }

    // VWorld webglMapInit.js uses document.write() to inject sub-scripts in dependency order.
    // Browsers block this from async scripts, so we collect the URLs and replay them serially.
    const originalWrite = document['write'].bind(document);
    const scriptQueue: string[] = [];

    document['write'] = (markup: string) => {
      const m = markup.match(/src=['"]([^'"]+)['"]/);
      if (m) scriptQueue.push(m[1]); // collect only src URLs — no markup injection
    };

    const script = document.createElement('script');
    const domain = window.location.host || 'localhost';
    script.src = `https://map.vworld.kr/js/webglMapInit.js.do?version=2.0&apiKey=${key}&domain=${domain}`;

    script.onerror = () => {
      document['write'] = originalWrite;
      setStatus('error');
      setErrorMsg('VWorld 3D 스크립트 로드 실패 (네트워크 또는 API 키 오류)');
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

      let attempts = 0;
      const timer = setInterval(() => {
        attempts++;
        if (window.vw) {
          clearInterval(timer);
          try {
            mapRef.current = new window.vw.Map(CONTAINER_ID, {
              apiKey: key,
              basemap: 'Satellite',
              center: new window.vw.Point(lon, lat, 0),
              zoom: 15,
              shadows: true,
            });
            setStatus('ready');
          } catch (e1) {
            try {
              window.vw.ol3?.load?.({
                mapDivId: CONTAINER_ID,
                apiKey: key,
                basemap: 'Satellite',
              });
              mapRef.current = window.vw.ol3?.map;
              setStatus('ready');
            } catch (e2) {
              console.error('[Map3D] init failed:', e1, e2);
              setStatus('error');
              setErrorMsg(`VWorld 3D 초기화 실패: ${(e1 as Error).message}`);
            }
          }
        } else if (attempts >= 50) {
          clearInterval(timer);
          setStatus('error');
          setErrorMsg('VWorld 3D 로드 실패 — VWorld 콘솔에서 localhost:5174 도메인 등록 확인');
        }
      }, 100);
    };

    document.head.appendChild(script);
    scriptRef.current = script;

    return () => {
      if (scriptRef.current && document.head.contains(scriptRef.current)) {
        document.head.removeChild(scriptRef.current);
        scriptRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;
    try {
      mapRef.current.moveTo?.([lon, lat], 15);
      mapRef.current.setCenter?.(new window.vw.Point(lon, lat, 0));
    } catch {
      // ignore pan errors
    }
  }, [lat, lon]);

  return (
    <div className="w-full h-full relative">
      <div id={CONTAINER_ID} ref={containerRef} className="w-full h-full" />

      {status === 'loading' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 text-gray-400">
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
