import { useEffect, useState, useCallback } from 'react';
import client from '../../api/client';

interface RewardConfig {
  id: number;
  user_type: string;
  eggs_per_period: number;
  period_days: number;
  is_active: boolean;
  rarity_filter: string;
}

interface RewardPin {
  id: number;
  user_id: number;
  dragon_id: number | null;
  dragon_name: string;
  egg_type: string;
  pin_code: string;
  config_id: number | null;
  issued_at: string;
  activated: boolean;
  activated_at: string | null;
  notified: boolean;
}

function RewardConfigs() {
  const [configs, setConfigs] = useState<RewardConfig[]>([]);
  const [load, setLoad] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ user_type: 'donor', eggs_per_period: 1, period_days: 30, is_active: true, rarity_filter: '' });

  const [pins, setPins] = useState<RewardPin[]>([]);
  const [pinTotal, setPinTotal] = useState(0);
  const [pinPage, setPinPage] = useState(1);
  const [pinLoad, setPinLoad] = useState(false);
  const [pinError, setPinError] = useState('');
  const [showPins, setShowPins] = useState(false);
  const PER_PAGE = 50;

  const fetchConfigs = useCallback(() => {
    client.get('/admin/reward-configs')
      .then((r) => setConfigs(r.data))
      .finally(() => setLoad(false));
  }, []);

  const fetchPins = useCallback((page: number) => {
    setPinLoad(true); setPinError('');
    client.get('/admin/reward-pins', { params: { page, per_page: PER_PAGE } })
      .then((r) => { setPins(r.data.items); setPinTotal(r.data.total); })
      .catch((e) => setPinError(e?.response?.data?.detail || 'Ошибка загрузки'))
      .finally(() => setPinLoad(false));
  }, []);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const resetForm = () => {
    setEditId(null);
    setForm({ user_type: 'donor', eggs_per_period: 1, period_days: 30, is_active: true, rarity_filter: '' });
  };

  const startEdit = (cfg: RewardConfig) => {
    setEditId(cfg.id);
    setForm({ user_type: cfg.user_type, eggs_per_period: cfg.eggs_per_period, period_days: cfg.period_days, is_active: cfg.is_active, rarity_filter: cfg.rarity_filter || '' });
  };

  const save = async () => {
    if (form.period_days < 1) { setError('Период должен быть >= 1 день'); return; }
    setSaving(true); setError(''); setSaved(false);
    try {
      if (editId) {
        await client.put(`/admin/reward-configs/${editId}`, form);
      } else {
        await client.post('/admin/reward-configs', form);
      }
      setSaved(true);
      resetForm();
      fetchConfigs();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    if (!confirm('Удалить конфигурацию?')) return;
    try {
      await client.delete(`/admin/reward-configs/${id}`);
      fetchConfigs();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const togglePins = () => {
    if (!showPins) {
      setPinPage(1);
      fetchPins(1);
    }
    setShowPins(!showPins);
  };

  const formatDate = (s: string) => {
    if (!s) return '—';
    try {
      const d = new Date(s.includes('T') ? s : s.replace(' ', 'T'));
      return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return s; }
  };

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header"><h2>🎁 Бесплатные яйца</h2></div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        {saved && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(120,200,120,0.12)', color: 'var(--success)', fontSize: 13 }}>Сохранено</div>}

        <div className="lair-card" style={{ marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 16px', color: 'var(--gold)', fontFamily: 'var(--font-title)' }}>
            {editId ? 'Изменить конфигурацию' : 'Новая конфигурация'}
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
            <div>
              <label className="lair-label">Тип пользователей</label>
              <select className="lair-input" value={form.user_type} onChange={(e) => setForm({ ...form, user_type: e.target.value })}>
                <option value="donor">Донатные</option>
                <option value="regular">Обычные</option>
              </select>
            </div>
            <div>
              <label className="lair-label">Яиц за период</label>
              <input className="lair-input" type="number" min={0} value={form.eggs_per_period}
                onChange={(e) => setForm({ ...form, eggs_per_period: Math.max(0, parseInt(e.target.value) || 0) })} />
            </div>
            <div>
              <label className="lair-label">Период (дней)</label>
              <input className="lair-input" type="number" min={1} value={form.period_days}
                onChange={(e) => setForm({ ...form, period_days: Math.max(1, parseInt(e.target.value) || 30) })} />
            </div>
            <div>
              <label className="lair-label">Редкости (через запятую, пусто=все)</label>
              <input className="lair-input" type="text" value={form.rarity_filter}
                placeholder="0,1,2,3"
                onChange={(e) => setForm({ ...form, rarity_filter: e.target.value })} />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}>
              <label className="lair-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: 0, padding: '10px 0' }}>
                <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
                Активна
              </label>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={save}>{saving ? '...' : editId ? 'Сохранить' : 'Создать'}</button>
            {editId && <button className="lair-btn lair-btn-outline" onClick={resetForm}>Отмена</button>}
          </div>
        </div>

        <div className="lair-card">
          <h3 style={{ margin: '0 0 16px', color: 'var(--gold)', fontFamily: 'var(--font-title)' }}>Конфигурации</h3>
          {configs.length === 0 ? (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>Нет конфигураций</div>
          ) : (
            <div className="lair-table-wrap" style={{ marginBottom: 16 }}>
              <table className="lair-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Тип</th>
                    <th>Яиц</th>
                    <th>Период</th>
                    <th>Редкости</th>
                    <th>Активна</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {configs.map((cfg) => (
                    <tr key={cfg.id}>
                      <td>{cfg.id}</td>
                      <td>{cfg.user_type === 'donor' ? 'Донатные' : 'Обычные'}</td>
                      <td>{cfg.eggs_per_period}</td>
                      <td>{cfg.period_days} дн.</td>
                      <td>{cfg.rarity_filter || 'Все'}</td>
                      <td>{cfg.is_active ? '✅' : '❌'}</td>
                      <td>
                        <button className="lair-btn lair-btn-sm" style={{ marginRight: 6 }} onClick={() => startEdit(cfg)}>✏</button>
                        <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => remove(cfg.id)}>✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="lair-card" style={{ marginTop: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: showPins ? 16 : 0 }}>
            <h3 style={{ margin: 0, color: 'var(--gold)', fontFamily: 'var(--font-title)' }}>Выданные PIN-коды</h3>
            <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={togglePins}>
              {showPins ? 'Скрыть' : 'Показать'}
            </button>
          </div>
          {showPins && (
            <>
              {pinError && <div style={{ padding: '10px 16px', marginBottom: 12, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{pinError}</div>}
              {pinLoad ? <div className="lair-skeleton" /> : (
                <>
                  <div className="lair-table-wrap">
                    <table className="lair-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>VK ID</th>
                          <th>Дракон</th>
                          <th>PIN</th>
                          <th>Активирован</th>
                          <th>Уведомлён</th>
                          <th>Дата выдачи</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pins.length === 0 ? (
                          <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Нет записей</td></tr>
                        ) : pins.map((p) => (
                          <tr key={p.id}>
                            <td>{p.id}</td>
                            <td>{p.user_id}</td>
                            <td>{p.dragon_name || p.egg_type || `#${p.dragon_id}`}</td>
                            <td style={{ fontFamily: 'var(--font-mono)' }}>{p.pin_code}</td>
                            <td>{p.activated ? `✅ ${p.activated_at ? formatDate(p.activated_at) : ''}` : '❌'}</td>
                            <td>{p.notified ? '✅' : '❌'}</td>
                            <td>{formatDate(p.issued_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {pinTotal > PER_PAGE && (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 12 }}>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" disabled={pinPage <= 1}
                        onClick={() => { const p = pinPage - 1; setPinPage(p); fetchPins(p); }}>◀</button>
                      <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{pinPage} / {Math.ceil(pinTotal / PER_PAGE)} (всего {pinTotal})</span>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" disabled={pinPage >= Math.ceil(pinTotal / PER_PAGE)}
                        onClick={() => { const p = pinPage + 1; setPinPage(p); fetchPins(p); }}>▶</button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default RewardConfigs;
