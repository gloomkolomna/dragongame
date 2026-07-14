import { useEffect, useState } from 'react';

interface Step {
  label: string;
  status: 'pending' | 'ok' | 'fail';
  detail?: string;
  ts: number;
}

const KEY = 'dragons_diag_steps';

function load(): Step[] {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // noop
  }
  return [];
}

let steps: Step[] = load();
const listeners = new Set<() => void>();

export function diagMark(label: string, status: Step['status'], detail?: string) {
  const step: Step = { label, status, detail, ts: Date.now() };
  steps = [...steps.filter((s) => s.label !== label), step];
  try {
    sessionStorage.setItem(KEY, JSON.stringify(steps));
  } catch {
    // noop
  }
  listeners.forEach((l) => l());
}

function DiagnosticOverlay() {
  const [open, setOpen] = useState(false);
  const [, force] = useState(0);

  useEffect(() => {
    const l = () => force((n) => n + 1);
    listeners.add(l);
    return () => { listeners.delete(l); };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'D' || e.key === 'd') setOpen((v) => !v);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const visible = open || steps.some((s) => s.status === 'fail');
  if (!visible) return null;

  const icon = (s: Step) =>
    s.status === 'ok' ? '✅' : s.status === 'fail' ? '❌' : '⏳';

  return (
    <div style={{
      position: 'fixed', top: 4, right: 4, zIndex: 10000,
      maxWidth: '92vw', maxHeight: '80vh', overflow: 'auto',
      background: 'rgba(10,0,20,0.95)', color: '#9f9',
      border: '1px solid #663', borderRadius: 6, padding: 8,
      fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 11, lineHeight: 1.4,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ color: '#fc6' }}>🔍 Диагностика</span>
        <button
          onClick={() => setOpen(false)}
          style={{ background: 'none', border: 'none', color: '#999', cursor: 'pointer', fontSize: 14 }}
        >✕</button>
      </div>
      {steps.length === 0 && <div style={{ color: '#666' }}>шагов пока нет</div>}
      {steps.map((s) => (
        <div key={s.label} style={{ marginBottom: 3, wordBreak: 'break-word' }}>
          <div>
            {icon(s)} <b style={{ color: '#ccf' }}>{s.label}</b>
            {s.detail && <span style={{ color: '#fc6' }}> — {s.detail}</span>}
          </div>
        </div>
      ))}
      <div style={{ marginTop: 6, color: '#666', fontSize: 10 }}>
        UA: {navigator.userAgent.slice(0, 60)}
      </div>
      <div style={{ marginTop: 4, display: 'flex', gap: 6 }}>
        <button
          onClick={() => { try { sessionStorage.clear(); localStorage.clear(); } catch { /* noop */ } location.reload(); }}
          style={{ background: '#533', color: '#fcc', border: 'none', borderRadius: 4, padding: '4px 8px', fontSize: 11, cursor: 'pointer' }}
        >Сброс</button>
        <button
          onClick={() => setOpen(false)}
          style={{ background: '#335', color: '#ccf', border: 'none', borderRadius: 4, padding: '4px 8px', fontSize: 11, cursor: 'pointer' }}
        >Закрыть</button>
      </div>
    </div>
  );
}

export default DiagnosticOverlay;
