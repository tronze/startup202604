import { useEffect, useRef } from 'react';

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

  useEffect(() => {
    const key = import.meta.env.VITE_VWORLD_KEY ?? '';

    if (!key || key === 'your_vworld_key_here') {
      // No VWorld key — show placeholder
      return;
    }

    const script = document.createElement('script');
    script.src = `https://map.vworld.kr/js/webglMapInit.js.do?version=2.0&apiKey=${key}`;
    script.async = true;
    script.onload = () => {
      if (!containerRef.current || !window.vw) return;
      try {
        mapRef.current = new window.vw.Map(CONTAINER_ID, {
          apiKey: key,
          basemap: 'Satellite',
          center: [lon, lat],
          zoom: 15,
          shadows: true,
        });

        mapRef.current?.on?.('load', () => {
          const sunScript = document.createElement('script');
          sunScript.src =
            'https://map.vworld.kr/js/dtkmap/tool3d/libapis/sunlightrights/sunlightrights_analysis_api.js';
          document.head.appendChild(sunScript);
        });
      } catch {
        // VWorld init can fail if the container isn't ready
      }
    };

    document.head.appendChild(script);
    scriptRef.current = script;

    return () => {
      if (scriptRef.current) {
        document.head.removeChild(scriptRef.current);
        scriptRef.current = null;
      }
    };
  }, []);

  // Pan to new coordinates when they change
  useEffect(() => {
    if (mapRef.current?.moveTo) {
      mapRef.current.moveTo([lon, lat], 15);
    }
  }, [lat, lon]);

  const key = import.meta.env.VITE_VWORLD_KEY ?? '';
  const hasKey = key && key !== 'your_vworld_key_here';

  return (
    <div className="w-full h-full relative">
      <div
        id={CONTAINER_ID}
        ref={containerRef}
        className="w-full h-full"
      />
      {!hasKey && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 text-gray-400">
          <div className="text-4xl mb-4">🌏</div>
          <p className="text-sm">3D 지도를 사용하려면</p>
          <p className="text-sm"><code className="bg-gray-800 px-2 py-1 rounded">VITE_VWORLD_KEY</code>를 설정하세요</p>
        </div>
      )}
    </div>
  );
}
