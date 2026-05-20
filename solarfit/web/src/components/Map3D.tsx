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

function flyCamera(viewer: any, lon: number, lat: number) {
  if (!viewer) return;
  try {
    const ellipsoid = viewer.scene?.globe?.ellipsoid;
    if (!ellipsoid) return;
    const destination = ellipsoid.cartographicToCartesian({
      longitude: lon * Math.PI / 180,
      latitude: lat * Math.PI / 180,
      height: 50000,
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
  // Unique ID per mount — prevents WebGL context pollution on React StrictMode double-mount
  const containerId = useRef(`vworld3d-${Math.random().toString(36).slice(2)}`);
  const viewerRef = useRef<any>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (viewerRef.current) {
      flyCamera(viewerRef.current, lon, lat);
    }
  }, [lat, lon]);

  useEffect(() => {
    let mounted = true;
    const cid = containerId.current;

    const key = import.meta.env.VITE_VWORLD_KEY ?? '';
    if (!key || key === 'your_vworld_key_here') {
      setStatus('error');
      setErrorMsg('VITE_VWORLD_KEY가 설정되지 않았습니다');
      return;
    }

    function initViewer() {
      if (!mounted) return;
      try {
        const viewer = window.ws3d.initViewer('#' + cid, true);
        if (!mounted) {
          try { viewer.destroy(); } catch { /* ignore */ }
          return;
        }
        viewerRef.current = viewer;

        const Cesium = window.Cesium;

        // VWorld 고해상도 위성 이미지 + 도로명 라벨 레이어
        try {
          viewer.imageryLayers.removeAll();
          viewer.imageryLayers.addImageryProvider(
            new Cesium.WebMapTileServiceImageryProvider({
              url: `https://api.vworld.kr/req/wmts/1.0.0/${key}/Satellite/GoogleMapsCompatible/{TileMatrix}/{TileRow}/{TileCol}.jpeg`,
              layer: 'Satellite', style: 'default', format: 'image/jpeg',
              tileMatrixSetID: 'GoogleMapsCompatible', maximumLevel: 19,
            })
          );
          viewer.imageryLayers.addImageryProvider(
            new Cesium.WebMapTileServiceImageryProvider({
              url: `https://api.vworld.kr/req/wmts/1.0.0/${key}/Hybrid/GoogleMapsCompatible/{TileMatrix}/{TileRow}/{TileCol}.png`,
              layer: 'Hybrid', style: 'default', format: 'image/png',
              tileMatrixSetID: 'GoogleMapsCompatible', maximumLevel: 19,
            })
          );
        } catch { /* keep ws3d default imagery */ }

        // LOD4 3D 건물 타일셋
        try {
          viewer.scene.primitives.add(
            new Cesium.Cesium3DTileset({
              url: `https://api.vworld.kr/req/3dls?key=${key}&domain=${window.location.host}&service=3DLS&request=GetTile&version=2.0&layer=lod4`,
            })
          );
        } catch { /* LOD4 없는 지역이면 무시 */ }

        setStatus('ready');
        const waitForScene = () => {
          if (!mounted || !viewerRef.current) return;
          if (viewer.scene?.globe?.ellipsoid) {
            flyCamera(viewer, lon, lat);
          } else {
            requestAnimationFrame(waitForScene);
          }
        };
        requestAnimationFrame(waitForScene);
      } catch (e) {
        if (!mounted) return;
        setStatus('error');
        setErrorMsg(`VWorld 3D 초기화 실패: ${(e as Error).message}`);
      }
    }

    if (window.ws3d?.initViewer) {
      initViewer();
      return () => {
        mounted = false;
        if (viewerRef.current?.destroy) {
          try { viewerRef.current.destroy(); } catch { /* ignore */ }
          viewerRef.current = null;
        }
      };
    }

    // VWorld webglMapInit.js calls document.write() — shim to collect sub-script URLs and load serially
    const origWrite = document['write'].bind(document);
    const scriptQueue: string[] = [];
    document['write'] = (markup: string) => {
      const m = markup.match(/src=['"]([^'"]+)['"]/);
      if (m) scriptQueue.push(m[1]);
    };

    const domain = window.location.host || 'localhost';
    const bootScript = document.createElement('script');
    bootScript.src = `https://map.vworld.kr/js/webglMapInit.js.do?version=2.0&apiKey=${key}&domain=${domain}`;

    bootScript.onerror = () => {
      document['write'] = origWrite;
      if (!mounted) return;
      setStatus('error');
      setErrorMsg('VWorld 스크립트 로드 실패 (네트워크 또는 API 키 오류)');
    };

    bootScript.onload = async () => {
      document['write'] = origWrite;
      for (const src of scriptQueue) {
        await new Promise<void>(resolve => {
          const s = document.createElement('script');
          s.src = src;
          s.onload = s.onerror = () => resolve();
          document.head.appendChild(s);
        });
      }
      if (!mounted) return;
      if (window.ws3d?.initViewer) {
        initViewer();
      } else {
        setStatus('error');
        setErrorMsg('VWorld 3D 로드 실패 — VWorld 콘솔에서 localhost:5174 도메인 등록 확인');
      }
    };

    document.head.appendChild(bootScript);

    return () => {
      mounted = false;
      document['write'] = origWrite;
      if (viewerRef.current?.destroy) {
        try { viewerRef.current.destroy(); } catch { /* ignore */ }
        viewerRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="w-full h-full relative">
      <div id={containerId.current} className="w-full h-full" />

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
