import { useEffect, useState } from 'react';
import client from '../../api/client';

interface DragonSet {
  id: number;
  name: string;
  quantity: number;
  discount_percent: number;
  donor_discount_percent: number;
  is_active: boolean;
}

const EMPTY = { name: '', quantity: 5, discount_percent: 0, donor_discount_percent: 0, is_active: true };

function DragonSets() {
  const [sets, setSets] = useState<DragonSet[]>([]);
  const [base, setBase] = useState(0);
  const [load, setLoad] = useState(true);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ ...EMPTY });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const reload = () => Promise.all([
    client.get('/admin/sets'),
    client.get('/admin/pricing'),
  ]).then(([s, p]) => { setSets(s.data); setBase(p.data.base_price_rub); }).finally(() => setLoad(false));

  useEffect(() => { reload(); }, []);

  const priceOf = (s: { quantity: number; discount_percent: number; donor_discount_percent: number }, donor: boolean) => {
    const d = donor ? s.donor_discount_percent : s.discount_percent;
    return Math.floor(s.quantity * base * (100 - d) / 100);
  };

  const startNew = () => { setEditId(null); setForm({ ...EMPTY }); setError(''); };
  const startEdit = (s: DragonSet) => {
    setEditId(s.id);
    setForm({
      name: s.name, quantity: s.quantity,
      discount_percent: s.discount_percent,
      donor_discount_percent: s.donor_discount_percent,
      is_active: s.is_active,
    });
    setError('');
  };

  const save = async () => {
    if (!form.name.trim()) { setError('Название обязательно'); return; }
    if (form.quantity < 1) { setError('Количество должно быть ≥ 1'); return; }
    setSaving(true); setError('');
    try {
      if (editId) {
        await client.put(`/admin/sets/${editId}`, form);
      } else {
        await client.post('/admin/sets', form);
      }
      startNew();
      await reload();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка');
    } finally {
      setSaving(false);
    }
  };

  const del = async (id: number) => {
    if (!window.confirm('Скрыть набор (сделать неактивным)?')) return;
    await client.delete(`/admin/sets/${id}`);
    await reload();
  };

  const num = (v: string) => Math.max(0, Number(v.replace(/\D/g, '')) || 0);

  return (
    <>
      <div className="lair-header"><h2>📦 Наборы драконов</h2></div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}

        <div className="lair-card" style={{ maxWidth: 640, marginBottom: 20 }}>
          <div style={{ fontWeight: 700, color: 'var(--gold)', marginBottom: 14 }}>
            {editId ? `Редактировать набор #${editId}` : 'Новый набор'}
          </div>
          <div style={{ marginBottom: 14 }}>
            <label className="lair-label">Название</label>
            <input className="lair-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="5 драконов" />
          </div>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 14 }}>
            <div>
              <label className="lair-label">Количество</label>
              <input className="lair-input" type="text" inputMode="numeric" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: num(e.target.value) })} style={{ width: 110 }} />
            </div>
            <div>
              <label className="lair-label">Скидка всем (%)</label>
              <input className="lair-input" type="text" inputMode="numeric" value={form.discount_percent} onChange={(e) => setForm({ ...form, discount_percent: num(e.target.value) })} style={{ width: 130 }} />
            </div>
            <div>
              <label className="lair-label">Скидка дона (%)</label>
              <input className="lair-input" type="text" inputMode="numeric" value={form.donor_discount_percent} onChange={(e) => setForm({ ...form, donor_discount_percent: num(e.target.value) })} style={{ width: 130 }} />
            </div>
          </div>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
              <span className="lair-label" style={{ margin: 0 }}>Активен</span>
            </label>
          </div>
          {base > 0 && form.quantity > 0 && (
            <div style={{ fontSize: 13, color: 'var(--parchment-dim)', marginBottom: 14 }}>
              Цена: <b style={{ color: 'var(--gold)' }}>{priceOf(form, false)}₽</b>
              {' · '}для дона: <b style={{ color: 'var(--gold)' }}>{priceOf(form, true)}₽</b>
            </div>
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={save}>{saving ? '...' : (editId ? 'Сохранить' : 'Добавить')}</button>
            {editId && <button className="lair-btn lair-btn-outline" onClick={startNew}>Отмена</button>}
          </div>
        </div>

        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          {load ? <div className="lair-skeleton" /> : (
            <table className="lair-table">
              <thead><tr><th style={{ width: 40 }}>#</th><th>Название</th><th>Кол-во</th><th>Скидка</th><th>Скидка дона</th><th>Цена</th><th>Цена дона</th><th style={{ width: 60 }}>Акт.</th><th style={{ width: 100 }}></th></tr></thead>
              <tbody>
                {sets.map((s) => (
                  <tr key={s.id} className="clickable" onClick={() => startEdit(s)} style={{ opacity: s.is_active ? 1 : 0.5 }}>
                    <td>{s.id}</td>
                    <td style={{ fontWeight: 600 }}>{s.name}</td>
                    <td>{s.quantity}</td>
                    <td>{s.discount_percent}%</td>
                    <td>{s.donor_discount_percent}%</td>
                    <td style={{ color: 'var(--gold)', fontWeight: 600 }}>{priceOf(s, false)}₽</td>
                    <td style={{ color: 'var(--gold)', fontWeight: 600 }}>{priceOf(s, true)}₽</td>
                    <td>{s.is_active ? '✅' : '❌'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={(e) => { e.stopPropagation(); startEdit(s); }}>✎</button>
                        <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={(e) => { e.stopPropagation(); del(s.id); }}>✕</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {sets.length === 0 && <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16 }}>Наборов пока нет</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

export default DragonSets;
