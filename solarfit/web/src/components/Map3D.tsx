import { useEffect, useRef } from 'react';

interface Props {
  lat: number;
  lon: number;
}

const KEY = import.meta.env.VITE_VWORLD_KEY ?? '';

export default function Map3D({ lat, lon }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // 좌표 바뀌면 iframe 안 지도로 postMessage
  useEffect(() => {
    iframeRef.current?.contentWindow?.postMessage({ type: 'flyTo', lat, lon }, '*');
  }, [lat, lon]);

  if (!KEY || KEY === 'your_vworld_key_here') {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900 text-red-400 text-sm">
        VITE_VWORLD_KEY가 설정되지 않았습니다
      </div>
    );
  }

  const src = `/vworld3d.html?key=${encodeURIComponent(KEY)}&lat=${lat}&lon=${lon}`;

  return (
    <iframe
      ref={iframeRef}
      src={src}
      className="w-full h-full border-0"
      title="VWorld 3D"
    />
  );
}
