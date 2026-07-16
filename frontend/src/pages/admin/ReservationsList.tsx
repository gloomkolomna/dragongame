import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface DragonOption {
  id: number;
  name: string;
  pin_code: string;
  egg_type: string;
  family_id: number | null;
  family_name: string;
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
  const [fBuyer, setFBuyer] = useState('');
  const [fDragon, setFDragon] = useState('');
  const [fPin, setFPin] = useState('');
  const [fStatus, setFStatus] = useState('');
  const [fNotes, setFNotes] = useState('');

  const [form, setForm] = useState({ vk_url: '', dragon_id: 0, notes: '' });
  const [showForm, setShowForm] = useState(false);
  const [dragonSearch, setDragonSearch] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!dropdownOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [dropdownOpen]);

  const navigate = useNavigate();

  const fetchReservations = useCallback(() => {
    client.get('/admin/reservations')
      .then((r) => setReservations(r.data))
      .catch((e) => setError(e?.response?.data?.detail || 'Ошибка загрузки'))
      .finally(() => setLoad(false));
  }, []);

  const fetchDragons = (vkUrl?: string) => {
    const params: any = {};
    if (vkUrl) params.exclude_vk_url = vkUrl;
    client.get('/admin/reservations/available-dragons', { params })
      .then((r) => setDragons(r.data))
      .catch(() => {});
  };

  useEffect(() => { fetchReservations(); fetchDragons(); }, [fetchReservations]);

  const handleFormVkChange = (url: string) => {
    setForm({ ...form, vk_url: url });
    if (url.length > 10) fetchDragons(url);
    else fetchDragons();
  };

  const handleCreate = async () => {
    if (!form.vk_url.trim()) { setError('Введите ссылку VK'); return; }
    if (!form.dragon_id) { setError('Выберите дракона'); return; }
    setSaving(true); setError('');
    try {
      await client.post('/admin/reservations', form);
      setShowForm(false);
      setForm({ vk_url: '', dragon_id: 0, notes: '' });
      setDragonSearch('');
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

  const uniqueBuyers = useMemo(() => {
    const set = new Set<string>();
    reservations.forEach((r) => { if (r.vk_name) set.add(r.vk_name); });
    return [...set].sort();
  }, [reservations]);

  const uniqueDragons = useMemo(() => {
    const set = new Set<string>();
    reservations.forEach((r) => { if (r.dragon_name) set.add(r.dragon_name); });
    return [...set].sort();
  }, [reservations]);

  const filtered = useMemo(() => {
    const tBuyer = fBuyer.toLowerCase().trim();
    const tDragon = fDragon.toLowerCase().trim();
    const tPin = fPin.toLowerCase().trim();
    const tNotes = fNotes.toLowerCase().trim();
    return reservations.filter((r) => {
      if (tBuyer) {
        const name = (r.vk_name || '').toLowerCase();
        const url = (r.vk_url || '').toLowerCase();
        const uid = r.vk_user_id ? String(r.vk_user_id) : '';
        if (!name.includes(tBuyer) && !url.includes(tBuyer) && !uid.includes(tBuyer)) return false;
      }
      if (tDragon) {
        const dn = (r.dragon_name || '').toLowerCase();
        const de = (r.egg_type || '').toLowerCase();
        if (!dn.includes(tDragon) && !de.includes(tDragon)) return false;
      }
      if (tPin && !(r.pin_code || '').toLowerCase().includes(tPin)) return false;
      if (tNotes && !(r.notes || '').toLowerCase().includes(tNotes)) return false;
      if (fStatus === 'active' && r.is_activated) return false;
      if (fStatus === 'done' && !r.is_activated) return false;
      return true;
    });
  }, [reservations, fBuyer, fDragon, fPin, fStatus, fNotes]);

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  const searchLower = dragonSearch.toLowerCase().trim();
  const filteredDragons = searchLower
    ? dragons.filter((d) =>
        d.name.toLowerCase().includes(searchLower) ||
        d.pin_code.toLowerCase().includes(searchLower) ||
        d.egg_type.toLowerCase().includes(searchLower) ||
        (d.family_name || '').toLowerCase().includes(searchLower)
      )
    : dragons;

  const selectedDragon = dragons.find((d) => d.id === form.dragon_id);

  return (
    <>
      <div className="lair-header">
        <h2>🔖 Бронирования драконов</h2>
        <span style={{ marginLeft: 'auto', color: 'var(--parchment-faded)', fontSize: 14 }}>{filtered.length} из {reservations.length}</span>
        <button className="lair-btn" style={{ marginLeft: 12 }} onClick={() => { setShowForm(!showForm); setError(''); setDragonSearch(''); fetchDragons(form.vk_url); }}>
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
                <input className="lair-input" type="text" value={form.vk_url} placeholder="https://vk.ru/id123456"
                  onChange={(e) => handleFormVkChange(e.target.value)} />
              </div>
              <div style={{ position: 'relative' }} ref={dropdownRef}>
                <label className="lair-label">Дракон (PIN — название) — доступно {dragons.length}</label>
                <input
                  className="lair-input"
                  type="text"
                  value={dragonSearch}
                  placeholder={selectedDragon ? `${selectedDragon.pin_code} — ${selectedDragon.name}` : 'Поиск дракона...'}
                  onFocus={() => setDropdownOpen(true)}
                  onChange={(e) => { setDragonSearch(e.target.value); setDropdownOpen(true); }}
                />
                {dropdownOpen && (
                  <div style={{
                    position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
                    maxHeight: 280, overflowY: 'auto', overflowX: 'hidden',
                    background: 'var(--parchment-dark)', border: '1px solid var(--border)',
                    borderRadius: '0 0 8px 8px', boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                  }}>
                    {filteredDragons.length === 0 ? (
                      <div style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: 13 }}>Ничего не найдено</div>
                    ) : (
                      (() => {
                        const groups: Record<string, typeof filteredDragons> = {};
                        const noFamily: typeof filteredDragons = [];
                        filteredDragons.forEach((d) => {
                          if (d.family_name) {
                            if (!groups[d.family_name]) groups[d.family_name] = [];
                            groups[d.family_name].push(d);
                          } else {
                            noFamily.push(d);
                          }
                        });
                        const sortedFamilies = Object.keys(groups).sort();
                        const elements: JSX.Element[] = [];
                        if (noFamily.length > 0) {
                          elements.push(
                            <div key="nofam">
                              <div style={{ padding: '4px 14px', fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, background: 'rgba(0,0,0,0.2)' }}>Без семейства ({noFamily.length})</div>
                              {noFamily.map((d) => (
                                <div
                                  key={d.id}
                                  onMouseDown={() => { setForm({ ...form, dragon_id: d.id }); setDragonSearch(''); setDropdownOpen(false); }}
                                  style={{
                                    padding: '8px 14px', cursor: 'pointer', fontSize: 13,
                                    color: 'var(--text)',
                                    background: form.dragon_id === d.id ? 'rgba(212,174,116,0.15)' : 'transparent',
                                  }}
                                  onMouseEnter={(e) => { (e.target as HTMLElement).style.background = 'rgba(212,174,116,0.2)'; }}
                                  onMouseLeave={(e) => { (e.target as HTMLElement).style.background = form.dragon_id === d.id ? 'rgba(212,174,116,0.15)' : 'transparent'; }}
                                >
                                  <span style={{ color: 'var(--gold)', fontWeight: 600 }}>{d.pin_code}</span> — {d.name} <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>({d.egg_type})</span>
                                </div>
                              ))}
                            </div>
                          );
                        }
                        sortedFamilies.forEach((fam) => {
                          const items = groups[fam];
                          elements.push(
                            <div key={fam}>
                              <div style={{ padding: '4px 14px', fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, background: 'rgba(0,0,0,0.2)' }}>{fam} ({items.length})</div>
                              {items.map((d) => (
                                <div
                                  key={d.id}
                                  onMouseDown={() => { setForm({ ...form, dragon_id: d.id }); setDragonSearch(''); setDropdownOpen(false); }}
                                  style={{
                                    padding: '8px 14px', cursor: 'pointer', fontSize: 13,
                                    color: 'var(--text)',
                                    background: form.dragon_id === d.id ? 'rgba(212,174,116,0.15)' : 'transparent',
                                  }}
                                  onMouseEnter={(e) => { (e.target as HTMLElement).style.background = 'rgba(212,174,116,0.2)'; }}
                                  onMouseLeave={(e) => { (e.target as HTMLElement).style.background = form.dragon_id === d.id ? 'rgba(212,174,116,0.15)' : 'transparent'; }}
                                >
                                  <span style={{ color: 'var(--gold)', fontWeight: 600 }}>{d.pin_code}</span> — {d.name} <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>({d.egg_type})</span>
                                </div>
                              ))}
                            </div>
                          );
                        });
                        return elements;
                      })()
                    )}
                  </div>
                )}
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
            Нет бронирований. Нажмите «+ Новая бронь».
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
                    <th>Статус</th>
                    <th>Заметка</th>
                    <th>Создано</th>
                    <th></th>
                  </tr>
                  <tr>
                    <th><input className="lair-input" value={fBuyer} onChange={(e) => setFBuyer(e.target.value)} placeholder="..." style={{ width: '100%', padding: '4px 8px', fontSize: 24, marginTop: 2 }} /></th>
                    <th><input className="lair-input" value={fDragon} onChange={(e) => setFDragon(e.target.value)} placeholder="..." style={{ width: '100%', padding: '4px 8px', fontSize: 24, marginTop: 2 }} /></th>
                    <th><input className="lair-input" value={fPin} onChange={(e) => setFPin(e.target.value)} placeholder="..." style={{ width: '100%', padding: '4px 8px', fontSize: 24, marginTop: 2 }} /></th>
                    <th>
                      <select className="lair-input" value={fStatus} onChange={(e) => setFStatus(e.target.value)}
                              style={{ width: '100%', padding: '4px 8px', fontSize: 24, marginTop: 2 }}>
                        <option value="">Все</option>
                        <option value="active">⏳ Ожидание</option>
                        <option value="done">✅ Активирован</option>
                      </select>
                    </th>
                    <th><input className="lair-input" value={fNotes} onChange={(e) => setFNotes(e.target.value)} placeholder="..." style={{ width: '100%', padding: '4px 8px', fontSize: 24, marginTop: 2 }} /></th>
                    <th></th>
                    <th></th>
                  </tr>
                  <tr>
                    <th>
                      <select className="lair-input" value={fBuyer} onChange={(e) => setFBuyer(e.target.value)}
                              style={{ width: '100%', padding: '4px 8px', fontSize: 24, marginTop: 2 }}>
                        <option value="">— Все покупатели —</option>
                        {uniqueBuyers.map((name) => (<option key={name} value={name}>{name}</option>))}
                      </select>
                    </th>
                    <th>
                      <select className="lair-input" value={fDragon} onChange={(e) => setFDragon(e.target.value)}
                              style={{ width: '100%', padding: '4px 8px', fontSize: 24, marginTop: 2 }}>
                        <option value="">— Все драконы —</option>
                        {uniqueDragons.map((name) => (<option key={name} value={name}>{name}</option>))}
                      </select>
                    </th>
                    <th></th>
                    <th></th>
                    <th></th>
                    <th></th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r) => (
                    <tr key={r.id} style={{ background: r.is_activated ? undefined : 'rgba(240,173,78,0.06)' }}>
                      <td>
                        {r.vk_name ? (
                          <a href={r.vk_url} target="_blank" rel="noopener noreferrer"
                            style={{ fontWeight: 600, fontSize: 14, color: 'var(--gold)', textDecoration: 'none' }}>
                            {r.vk_name}
                          </a>
                        ) : (
                          <a href={r.vk_url} target="_blank" rel="noopener noreferrer"
                            style={{ color: 'var(--gold)', fontSize: 13 }}>
                            {r.vk_url.length > 30 ? r.vk_url.slice(0, 30) + '...' : r.vk_url}
                          </a>
                        )}
                        {r.vk_user_id && <div style={{ fontSize: 11, color: 'var(--parchment-faded)' }}>ID: {r.vk_user_id}</div>}
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
