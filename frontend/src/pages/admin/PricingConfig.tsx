import { useEffect, useState } from 'react';
import client from '../../api/client';

function PricingConfig({ hideHeader }: { hideHeader?: boolean }) {
  const [price, setPrice] = useState(0);
  const [load, setLoad] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    client.get('/admin/pricing')
      .then((r) => setPrice(r.data.base_price_rub))
      .finally(() => setLoad(false));
  }, []);

  const save = async () => {
    if (price < 0) { setError('Цена не может быть отрицательной'); return; }
    setSaving(true); setError(''); setSaved(false);
    try {
      const r = await client.put('/admin/pricing', { base_price_rub: price });
      setPrice(r.data.base_price_rub);
      setSaved(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка');
    } finally {
      setSaving(false);
    }
  };

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      {!hideHeader && <div className="lair-header"><h2>💰 Стоимость одного яйца</h2></div>}
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        {saved && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(120,200,120,0.12)', color: 'var(--success)', fontSize: 13 }}>Сохранено</div>}
        <div className="lair-card" style={{ maxWidth: 420 }}>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Стоимость одного яйца (₽)</label>
            <input
              className="lair-input"
              type="text"
              inputMode="numeric"
              value={price}
              onChange={(e) => { setSaved(false); setPrice(Math.max(0, Number(e.target.value.replace(/\D/g, '')) || 0)); }}
              style={{ width: 160, fontSize: 18, fontFamily: 'var(--font-mono)' }}
            />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              Базовая цена за 1 дракона (1 PIN). Скидки наборов считаются от неё.
            </div>
          </div>
          <button className="lair-btn" disabled={saving} onClick={save}>{saving ? '...' : 'Сохранить'}</button>
        </div>
      </div>
    </>
  );
}

export default PricingConfig;
