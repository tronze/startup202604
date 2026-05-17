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

    const script = document.createElement('script');
    const domain = encodeURIComponent(window.location.hostname || 'localhost');
    script.src = `https://map.vworld.kr/js/webglMapInit.js.do?version=2.0&apiKey=${key}&domain=${domain}`;
    script.async = true;

    script.onerror = () => {
      setStatus('error');
      setErrorMsg('VWorld 3D 스크립트 로드 실패 (네트워크 또는 API 키 오류)');
    };

    script.onload = () => {
      // VWorld 3D initializes window.vw asynchronously after script load — poll up to 5s
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
              console.error('VWorld 3D init failed:', e1, e2);
              setStatus('error');
              setErrorMsg(`VWorld 3D 초기화 실패: ${(e1 as Error).message}`);
            }
          }
        } else if (attempts >= 50) {
          clearInterval(timer);
          setStatus('error');
          setErrorMsg('VWorld API가 로드되지 않았습니다 — VWorld 콘솔에서 localhost 도메인을 API 키에 등록하세요');
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
