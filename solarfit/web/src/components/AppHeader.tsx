type View = 'home' | 'dashboard' | 'explore';

interface Props {
  activeView: View;
  onChange: (view: View) => void;
}

export default function AppHeader({ activeView, onChange }: Props) {
  return (
    <header className="h-14 shrink-0 border-b border-gray-800 bg-gray-950/95 text-white">
      <div className="flex h-full items-center justify-between px-5">
        <button
          className="flex items-center gap-2 text-left"
          onClick={() => onChange('home')}
          aria-label="SolarFit 홈으로 이동"
        >
          <span className="grid h-8 w-8 place-items-center rounded bg-yellow-400 text-sm font-black text-gray-950">
            SF
          </span>
          <span>
            <span className="block text-sm font-semibold leading-4">SolarFit</span>
            <span className="block text-[11px] text-gray-500">Factory Solar Intelligence</span>
          </span>
        </button>

        <nav className="flex items-center gap-1 rounded bg-gray-900 p-1">
          <button
            onClick={() => onChange('home')}
            className={`rounded px-4 py-2 text-sm font-medium transition-colors ${
              activeView === 'home'
                ? 'bg-yellow-400 text-gray-950'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            }`}
          >
            홈
          </button>
          <button
            onClick={() => onChange('dashboard')}
            className={`rounded px-4 py-2 text-sm font-medium transition-colors ${
              activeView === 'dashboard'
                ? 'bg-yellow-400 text-gray-950'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            }`}
          >
            대시보드
          </button>
          <button
            onClick={() => onChange('explore')}
            className={`rounded px-4 py-2 text-sm font-medium transition-colors ${
              activeView === 'explore'
                ? 'bg-yellow-400 text-gray-950'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            }`}
          >
            새로 모색
          </button>
        </nav>
      </div>
    </header>
  );
}
