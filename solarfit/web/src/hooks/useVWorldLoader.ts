import { useEffect, useState } from 'react';

declare global {
  interface Window {
    vw: any;
    $: any;
    jQuery: any;
  }
}

let _loaderPromise: Promise<void> | null = null;

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`스크립트 로드 실패: ${src}`));
    document.head.appendChild(s);
  });
}

function getLoaderPromise(key: string): Promise<void> {
  if (window.vw?.Map) return Promise.resolve();
  if (_loaderPromise) return _loaderPromise;

  _loaderPromise = (async () => {
    if (!window.jQuery) {
      await loadScript('https://code.jquery.com/jquery-3.7.1.min.js');
    }

    const scriptQueue: string[] = [];
    const origWrite = document['write'].bind(document);
    document['write'] = (markup: string) => {
      const m = markup.match(/src=["']([^"']+)["']/);
      if (m) scriptQueue.push(new URL(m[1], 'https://map.vworld.kr').href);
    };

    try {
      await loadScript(
        `https://map.vworld.kr/js/webglMapInit.js.do?version=3.0&apiKey=${encodeURIComponent(key)}`
      );
    } finally {
      document['write'] = origWrite;
    }

    for (const src of scriptQueue) {
      await loadScript(src);
    }

    if (!window.vw?.Map) throw new Error('VWorld 3D API 초기화 실패');
  })();

  _loaderPromise.catch(() => { _loaderPromise = null; });
  return _loaderPromise;
}

export type LoaderState = 'loading' | 'ready' | { error: string };

export function useVWorldLoader(): LoaderState {
  const [state, setState] = useState<LoaderState>(() =>
    window.vw?.Map ? 'ready' : 'loading'
  );

  useEffect(() => {
    const key = import.meta.env.VITE_VWORLD_KEY ?? '';
    if (!key || key === 'your_vworld_key_here') {
      setState({ error: 'VITE_VWORLD_KEY가 설정되지 않았습니다' });
      return;
    }
    if (window.vw?.Map) {
      setState('ready');
      return;
    }
    getLoaderPromise(key)
      .then(() => setState('ready'))
      .catch((e: Error) => setState({ error: e.message }));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return state;
}
