import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface DragonOption {
  id: number;
  name: string;
  pin_code: string;
  egg_type: string;
}

interface Reservation {
  id: number;
  vk_url: string;
  vk_user_id: number | null;
  vk_name: string;
  dragon_id: number;
  dragon_name: string;
  egg_type: string;
  pin_code: string;
  is_activated: boolean;
  activated_at: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

function ReservationsList() {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [dragons, setDragons] = useState<DragonOption[]>([]);
  const [load, setLoad] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');

  const [form, setForm] = useState({ vk_url: '', dragon_id: 0, notes: '' });
  const [showForm, setShowForm] = useState(false);

  const navigate = useNavigate();

  const fetchReservations = useCallback(() => {
    client.get('/admin/reservations', { params: { search } })
      .then((r) => setReservations(r.data))
      .catch((e) => setError(e?.response?.data?.detail || 'Ошибка загрузки'))
      .finally(() => setLoad(false));
  }, [search]);

  const fetchDragons = (vkUrl?: string) => {
    const params: any = {};
    if (vkUrl) params.exclude_vk_url = vkUrl;
    client.get('/admin/reservations/available-dragons', { params })
      .then((r) => setDragons(r.data))
      .catch(() => {});
  };

  useEffect(() => {
    fetchReservations();
    fetchDragons();
  }, [fetchReservations]);

  const handleSearchChange = (val: string) => {
    setSearch(val);
    setLoad(true);
  };

  const handleFormVkChange = (url: string) => {
    setForm({ ...form, vk_url: url });
    if (url.length > 10) {
      fetchDragons(url);
    } else {
      fetchDragons();
    }
  };

  const handleCreate = async () => {
    if (!form.vk_url.trim()) { setError('Введите ссылку VK'); return; }
    if (!form.dragon_id) { setError('Выберите дракона'); return; }
    setSaving(true); setError('');
    try {
      await client.post('/admin/reservations', form);
      setShowForm(false);
      setForm({ vk_url: '', dragon_id: 0, notes: '' });
      fetchReservations();
      fetchDragons();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить бронь?')) return;
    try {
      await client.delete(`/admin/reservations/${id}`);
      fetchReservations();
      fetchDragons();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка');
    }
  };

  const formatDate = (s: string | null) => {
    if (!s) return '—';
    try {
      const d = new Date(s.includes('T') ? s : s.replace(' ', 'T'));
      return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return s; }
  };

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header">
        <h2>🔖 Бронирования драконов</h2>
        <input
          className="lair-input"
          type="text"
          placeholder="Поиск по имени или ссылке..."
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          style={{ marginLeft: 16, width: 260, fontSize: 14 }}
        />
        <span style={{ marginLeft: 'auto', color: 'var(--parchment-faded)', fontSize: 14 }}>{reservations.length} записей</span>
        <button className="lair-btn" style={{ marginLeft: 12 }} onClick={() => { setShowForm(!showForm); setError(''); fetchDragons(form.vk_url); }}>
          {showForm ? 'Скрыть' : '+ Новая бронь'}
        </button>
      </div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}

        {showForm && (
          <div className="lair-card" style={{ marginBottom: 24 }}>
            <h3 style={{ margin: '0 0 16px', color: 'var(--gold)', fontFamily: 'var(--font-title)' }}>Новая бронь</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12, marginBottom: 16, alignItems: 'end' }}>
              <div>
                <label className="lair-label">Ссылка VK</label>
                <input className="lair-input" type="text" value={form.vk_url} placeholder="https://vk.com/id123456"
                  onChange={(e) => handleFormVkChange(e.target.value)} />
              </div>
              <div>
                <label className="lair-label">Дракон (PIN — название)</label>
                <select className="lair-input" value={form.dragon_id} onChange={(e) => setForm({ ...form, dragon_id: parseInt(e.target.value) || 0 })}>
                  <option value={0}>— Выберите —</option>
                  {dragons.map((d) => (
                    <option key={d.id} value={d.id}>{d.pin_code} — {d.name} ({d.egg_type})</option>
                  ))}
                </select>
              </div>
              <div>
                <button className="lair-btn" disabled={saving} onClick={handleCreate}>
                  {saving ? '...' : 'Создать'}
                </button>
              </div>
            </div>
            <div>
              <label className="lair-label">Заметка</label>
              <input className="lair-input" type="text" value={form.notes} placeholder="Необязательно"
                onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </div>
          </div>
        )}

        {reservations.length === 0 ? (
          <div className="lair-card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            {search ? 'Ничего не найдено.' : 'Нет бронирований. Нажмите «+ Новая бронь».'}
          </div>
        ) : (
          <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
            <div className="lair-table-responsive">
              <table className="lair-table">
                <thead>
                  <tr>
                    <th>Покупатель</th>
                    <th>Дракон</th>
                    <th>PIN</th>
                    <th>Активирован</th>
                    <th>Заметка</th>
                    <th>Создано</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {reservations.map((r) => (
                    <tr key={r.id} style={{ background: r.is_activated ? undefined : 'rgba(240,173,78,0.06)' }}>
                      <td>
                        {r.vk_name ? (
                          <span style={{ fontWeight: 600, fontSize: 14 }}>{r.vk_name}</span>
                        ) : (
                          <a href={r.vk_url} target="_blank" rel="noopener noreferrer"
                            style={{ color: 'var(--gold)', fontSize: 13 }}>
                            {r.vk_url.length > 30 ? r.vk_url.slice(0, 30) + '...' : r.vk_url}
                          </a>
                        )}
                        {r.vk_user_id && !r.vk_name && <div style={{ fontSize: 11, color: 'var(--parchment-faded)' }}>ID: {r.vk_user_id}</div>}
                      </td>
                      <td>
                        <span style={{ cursor: 'pointer', color: 'var(--gold)', fontWeight: 600, fontSize: 14 }}
                          onClick={() => navigate(`/admin/dragons/${r.dragon_id}/edit`)}>
                          {r.dragon_name || r.egg_type || `#${r.dragon_id}`}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600 }}>{r.pin_code}</td>
                      <td>
                        {r.is_activated ? (
                          <span style={{ color: '#5cb85c', fontWeight: 600, fontSize: 13 }}>
                            ✅ {r.activated_at ? formatDate(r.activated_at) : ''}
                          </span>
                        ) : (
                          <span style={{ color: '#f0ad4e', fontWeight: 600, fontSize: 13 }}>⏳ Ожидание</span>
                        )}
                      </td>
                      <td style={{ fontSize: 13, maxWidth: 150, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={r.notes}>
                        {r.notes || '—'}
                      </td>
                      <td style={{ fontSize: 12, whiteSpace: 'nowrap' }}>{formatDate(r.created_at)}</td>
                      <td>
                        <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ marginRight: 4 }}
                          onClick={() => navigate(`/admin/dragons/${r.dragon_id}/edit`)}>
                          🔍
                        </button>
                        <button className="lair-btn lair-btn-sm lair-btn-danger"
                          onClick={() => handleDelete(r.id)}>
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default ReservationsList;
