interface Props {
  onSelect: (lat: number, lon: number) => void;
}

export default function SearchBar({ onSelect: _onSelect }: Props) {
  return <div data-testid="search-bar" />;
}
