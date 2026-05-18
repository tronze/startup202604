import { useState } from 'react';
import { searchAddress } from '../api';
import type { SearchResult } from '../types';

interface Props {
  onSelect: (lat: number, lon: number) => void;
}

export default function SearchBar({ onSelect }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const data = await searchAddress(query);
      setResults(data);
      setOpen(data.length > 0);
    } catch {
      setResults([]);
      setOpen(false);
    } finally {
      setSearching(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') handleSearch();
  }

  return (
    <div className="absolute top-4 left-4 z-[1000] w-80">
      <div className="flex bg-white rounded-lg shadow-lg overflow-hidden">
        <input
          className="flex-1 px-4 py-2 text-gray-900 text-sm outline-none"
          placeholder="주소 또는 장소명 검색..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          className="px-4 bg-yellow-400 text-gray-900 font-bold hover:bg-yellow-300 disabled:opacity-50"
        >
          {searching ? '...' : '검색'}
        </button>
      </div>
      {open && results.length > 0 && (
        <div className="mt-1 bg-white rounded-lg shadow-lg overflow-hidden">
          {results.map((r, i) => (
            <button
              key={i}
              className="w-full text-left px-4 py-2 text-sm text-gray-900 hover:bg-yellow-50 border-b last:border-b-0"
              onClick={() => {
                onSelect(r.lat, r.lon);
                setQuery(r.title);
                setOpen(false);
              }}
            >
              <div className="font-medium">{r.title}</div>
              {r.address && <div className="text-gray-500 text-xs">{r.address}</div>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
