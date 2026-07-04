import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import client from '../../api/client';

const GROUP_ID = 239999455;

interface User { vk_id: number; first_name: string; last_name: string; state: string; registered_at: string; pins_activated: number; last_pin_code: string | null; dragons_collected: number; current_dragon_id: number | null; current_step: number; }
interface Detail { vk_id: number; first_name: string; last_name: string; registered_at: string; pins_activated: number; pins: { code: string; dragon_name: string; egg_type: string; status: string; activated_at: string }[]; dragons: { dragon_id: number; name: string | null; egg_type: string; status: string; progress_pct: number; completed_at: string | null }[]; dragons_collected: number; dragons_active: number; dragons_total: number; }

function UsersList() {
  const [users, setUsers] = useState<User[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [load, setLoad] = useState(true);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    client.get('/admin/users').then((r) => {
      setUsers(r.data);
      const uid = searchParams.get('vk_id');
      if (uid) show(Number(uid));
    }).finally(() => setLoad(false));
  }, []);

  const show = async (id: number) => {
    const r = await client.get(`/admin/users/${id}`);
    setDetail(r.data);
    setSearchParams({ vk_id: String(id) });
  };

  const restartDragon = async (vkId: number, dragonId: number) => {
    if (!window.confirm('Возобновить выращивание этого дракона заново?')) return;
    try {
      await client.post(`/admin/users/${vkId}/dragons/${dragonId}/restart`);
      show(vkId);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
  };

  const deleteDragon = async (vkId: number, dragonId: number) => {
    if (!window.confirm('Удалить этого дракона у игрока? Прогресс будет потерян.')) return;
    try {
      await client.delete(`/admin/users/${vkId}/dragons/${dragonId}`);
      show(vkId);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
  };

  const profileUrl = (vkId: number) => `https://vk.com/id${vkId}`;
  const chatUrl = (vkId: number) => `https://vk.com/gim${GROUP_ID}?sel=${vkId}`;

  return (
    <>
      <div className="lair-header"><h2>👥 Игроки</h2></div>
      <div className="lair-content">
        {detail ? (
          <div className="lair-rise">
            <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => { setDetail(null); setSearchParams({}); }} style={{ marginBottom: 16 }}>← Назад</button>
            <div className="lair-card" style={{ marginBottom: 16 }}>
              <h3 style={{ color: 'var(--gold)', margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
                <a href={profileUrl(detail.vk_id)} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--gold)', textDecoration: 'none' }}>
                  {[detail.last_name, detail.first_name].filter(Boolean).join(' ') || `id${detail.vk_id}`}
                </a>
                <a href={chatUrl(detail.vk_id)} target="_blank" rel="noopener noreferrer"
                   className="lair-btn lair-btn-sm lair-btn-outline"
                   style={{ textDecoration: 'none', fontSize: 13, padding: '2px 8px' }}
                   title="Чат в боте">💬</a>
              </h3>
              <p style={{ color: 'var(--parchment-dim)', fontSize: 14 }}>
                🥚 Активно: {detail.dragons_active} &nbsp;|&nbsp; ⭐ Выращено: {detail.dragons_collected} &nbsp;|&nbsp; 🐉 Всего: {detail.dragons_total}
              </p>
            </div>

            <div className="lair-card" style={{ marginBottom: 16 }}>
              <h4 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>Коллекция</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 6 }}>
                {detail.dragons.map((d) => (
                  <div key={d.dragon_id} className="lair-grid-cell" style={{ textAlign: 'center', padding: 12 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{d.name || d.egg_type}</div>
                    <div style={{ fontSize: 12, marginTop: 4 }}>{d.status === 'completed' ? '⭐' : d.status === 'growing' ? `${d.progress_pct}%` : '🔒'}</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, alignItems: 'center', marginTop: 6 }}>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ fontSize: 11, width: '100%' }}
                              onClick={() => navigate(`/admin/users/${detail.vk_id}/dragons/${d.dragon_id}/progress`)}>
                        📋 Прогресс
                      </button>
                      <div style={{ display: 'flex', gap: 4, width: '100%' }}>
                        {d.status === 'completed' && (
                          <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ fontSize: 11, flex: 1 }}
                                  onClick={() => restartDragon(detail.vk_id, d.dragon_id)}>🔄 Заново</button>
                        )}
                        <button className="lair-btn lair-btn-sm lair-btn-danger" style={{ fontSize: 11, flex: 1 }}
                                onClick={() => deleteDragon(detail.vk_id, d.dragon_id)}>✕ Удалить</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : load ? (
          <div className="lair-skeleton" />
        ) : (
          <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="lair-table">
              <thead><tr><th>Игрок</th><th>🐉</th><th>Текущий</th><th>Дата рег.</th><th style={{ width: 80 }}>Чат</th></tr></thead>
              <tbody>{users.map((u) => {
                const name = [u.first_name, u.last_name].filter(Boolean).join(' ') || `id${u.vk_id}`;
                return (
                  <tr key={u.vk_id} className="clickable" onClick={() => show(u.vk_id)}>
                    <td>
                      <a href={profileUrl(u.vk_id)} target="_blank" rel="noopener noreferrer"
                         onClick={(e) => e.stopPropagation()} style={{ color: 'var(--gold)' }}>
                        {name}
                      </a>
                      <div style={{ fontSize: 12, color: 'var(--parchment-faded)' }}>id{u.vk_id}</div>
                    </td>
                    <td>{u.dragons_collected}</td>
                    <td style={{ fontSize: 14 }}>{u.state === 'idle' ? '—' : `шаг ${u.current_step}`}</td>
                    <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{u.registered_at?.slice(0, 10)}</td>
                    <td>
                      <a href={chatUrl(u.vk_id)} target="_blank" rel="noopener noreferrer"
                         onClick={(e) => e.stopPropagation()}
                         className="lair-btn lair-btn-sm lair-btn-outline"
                         style={{ textDecoration: 'none', fontSize: 12 }}>💬</a>
                    </td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

export default UsersList;
