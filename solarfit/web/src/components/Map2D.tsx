import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface Props {
  onMapClick: (lat: number, lon: number) => void;
  selectedCoords: { lat: number; lon: number } | null;
}

export default function Map2D({ onMapClick, selectedCoords }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current).setView([34.57, 126.60], 11);

    const vworldKey = import.meta.env.VITE_VWORLD_KEY;
    if (vworldKey && vworldKey !== 'your_vworld_key_here') {
      L.tileLayer(
        `https://api.vworld.kr/req/wmts/1.0.0/${vworldKey}/Base/{z}/{y}/{x}.png`,
        { attribution: '© VWorld', maxZoom: 19 }
      ).addTo(map);
    } else {
      // Fallback to OpenStreetMap if no VWorld key
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);
    }

    map.on('click', (e) => {
      onMapClick(e.latlng.lat, e.latlng.lng);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !selectedCoords) return;
    if (markerRef.current) {
      markerRef.current.remove();
    }
    markerRef.current = L.marker([selectedCoords.lat, selectedCoords.lon], {
      icon: L.divIcon({
        className: '',
        html: '<div style="background:#FBBF24;width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4)"></div>',
        iconAnchor: [8, 8],
      }),
    }).addTo(mapRef.current);
  }, [selectedCoords]);

  return <div ref={containerRef} className="w-full h-full" />;
}
