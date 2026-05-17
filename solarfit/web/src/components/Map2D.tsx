interface Props {
  onMapClick: (lat: number, lon: number) => void;
  selectedCoords: { lat: number; lon: number } | null;
}

export default function Map2D({ onMapClick: _click, selectedCoords: _coords }: Props) {
  return <div data-testid="map-2d" className="w-full h-full bg-gray-800" />;
}
