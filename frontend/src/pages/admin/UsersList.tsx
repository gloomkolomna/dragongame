import { useEffect, useState } from 'react';
import client from '../../api/client';

interface User { vk_id: number; state: string; registered_at: string; pins_activated: number; last_pin_code: string | null; dragons_collected: number; current_dragon_id: number | null; current_step: number; }
interface Detail { vk_id: number; registered_at: string; pins_activated: number; pins: { code: string; dragon_name: string; egg_type: string; status: string; activated_at: string }[]; dragons: { dragon_id: number; name: string | null; egg_type: string; status: string; progress_pct: number; completed_at: string | null }[]; dragons_collected: number; dragons_total: number; }

function UsersList() {
  const [users, setUsers] = useState<User[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [load, setLoad] = useState(true);

  useEffect(() => { client.get('/admin/users').then((r) => setUsers(r.data)).finally(() => setLoad(false)); }, []);

  const show = async (id: number) => { const r = await client.get(`/admin/users/${id}`); setDetail(r.data); };
  const skip = async (id: number) => { await client.post(`/admin/users/${id}/skip-step`); show(id); };
  const reset = async (id: number) => { if (!window.confirm('Сбросить всё выращивание?')) return; await client.post(`/admin/users/${id}/reset-dragon`); setDetail(null); };

  return (
    <>
      <div className="lair-header"><h2>👥 Игроки</h2></div>
      <div className="lair-content">
        {detail ? (
          <div className="lair-rise">
            <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => setDetail(null)} style={{ marginBottom: 16 }}>← Назад</button>
            <div className="lair-card" style={{ marginBottom: 16 }}>
              <h3 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>Игрок VK ID: {detail.vk_id}</h3>
              <p style={{ color: 'var(--parchment-dim)', fontSize: 13 }}>Выращено: {detail.dragons_collected}/{detail.dragons_total}</p>
            </div>
            <div className="lair-card" style={{ marginBottom: 16 }}>
              <h4 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>Коллекция</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 6 }}>
                {detail.dragons.map((d) => (
                  <div key={d.dragon_id} className="lair-grid-cell" style={{ textAlign: 'center', padding: 12 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{d.name || d.egg_type}</div>
                    <div style={{ fontSize: 11, marginTop: 4 }}>{d.status === 'completed' ? '⭐' : d.status === 'growing' ? `${d.progress_pct}%` : '🔒'}</div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="lair-btn" onClick={() => skip(detail.vk_id)}>⏭ Скип шага</button>
              <button className="lair-btn lair-btn-danger" onClick={() => reset(detail.vk_id)}>🔄 Сбросить</button>
            </div>
          </div>
        ) : load ? (
          <div className="lair-skeleton" />
        ) : (
          <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="lair-table">
              <thead><tr><th>VK ID</th><th>Выращено</th><th>Текущий</th><th>Дата рег.</th></tr></thead>
              <tbody>{users.map((u) => (
                <tr key={u.vk_id} className="clickable" onClick={() => show(u.vk_id)}>
                  <td>{u.vk_id}</td>
                  <td>{u.dragons_collected}</td>
                  <td style={{ fontSize: 13 }}>{u.state === 'idle' ? '—' : `шаг ${u.current_step}`}</td>
                  <td style={{ fontSize: 12, color: 'var(--parchment-faded)' }}>{u.registered_at?.slice(0, 10)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

export default UsersList;
