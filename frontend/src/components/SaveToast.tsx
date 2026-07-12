import { useEffect, useState } from 'react';

interface Toast {
  id: number;
  text: string;
}

let counter = 0;

function SaveToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const onSaved = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      const text = (detail && detail.text) || '✅ Сохранено';
      const id = ++counter;
      setToasts((prev) => [...prev, { id, text }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 2500);
    };
    window.addEventListener('admin:saved', onSaved);
    return () => window.removeEventListener('admin:saved', onSaved);
  }, []);

  return (
    <div style={{ position: 'fixed', left: 16, bottom: 16, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 8 }}>
      {toasts.map((t) => (
        <div
          key={t.id}
          style={{
            background: 'var(--success-bg)',
            color: 'var(--parchment)',
            border: '1px solid #3a8a65',
            borderRadius: 8,
            padding: '10px 16px',
            fontSize: 14,
            fontFamily: 'var(--font-body)',
            boxShadow: '0 6px 20px rgba(0, 0, 0, 0.45)',
            animation: 'toastSlideIn 0.25s ease',
          }}
        >
          {t.text}
        </div>
      ))}
    </div>
  );
}

export default SaveToast;
