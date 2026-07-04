import { useEffect, useState } from 'react';
import client from '../../api/client';

const GROUP_ID = 239999455;

interface User { vk_id: number; first_name: string; last_name: string; state: string; registered_at: string; pins_activated: number; last_pin_code: string | null; dragons_collected: number; current_dragon_id: number | null; current_step: number; }
interface Detail { vk_id: number; registered_at: string; pins_activated: number; pins: { code: string; dragon_name: string; egg_type: string; status: string; activated_at: string }[]; dragons: { dragon_id: number; name: string | null; egg_type: string; status: string; progress_pct: number; completed_at: string | null }[]; dragons_collected: number; dragons_total: number; }
interface StepInfo { step_number: number; task_description: string; magic_action: string; hint: string; completed: boolean; current: boolean; }
interface StepsData { dragon_name: string; total: number; current_step: number; steps: StepInfo[]; }

function UsersList() {
  const [users, setUsers] = useState<User[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [stepsData, setStepsData] = useState<StepsData | null>(null);
  const [load, setLoad] = useState(true);

  useEffect(() => { client.get('/admin/users').then((r) => setUsers(r.data)).finally(() => setLoad(false)); }, []);

  const show = async (id: number) => {
    const r = await client.get(`/admin/users/${id}`);
    setDetail(r.data); setStepsData(null);
    // Если есть активный дракон — загружаем шаги
    try {
      const s = await client.get(`/admin/users/${id}/steps`);
      setStepsData(s.data);
    } catch (e) {
      setStepsData(null);
    }
  };

  const toggleStep = async (id: number, stepNum: number) => {
    await client.post(`/admin/users/${id}/steps/${stepNum}/toggle`);
    show(id);
  };

  const resetProgress = async (id: number) => {
    if (!window.confirm('Сбросить весь прогресс по этому дракону?')) return;
    try {
      await client.post(`/admin/users/${id}/reset-dragon`);
      setStepsData(null);
      show(id);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
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
            <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => { setDetail(null); setStepsData(null); }} style={{ marginBottom: 16 }}>← Назад</button>
            <div className="lair-card" style={{ marginBottom: 16 }}>
              <h3 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>
                Игрок{' '}
                <a href={profileUrl(detail.vk_id)} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--gold)' }}>
                  VK ID: {detail.vk_id}
                </a>
              </h3>
              <p style={{ color: 'var(--parchment-dim)', fontSize: 14 }}>Выращено: {detail.dragons_collected}/{detail.dragons_total}</p>
            </div>

            {stepsData && stepsData.steps.length > 0 && (
              <div className="lair-card" style={{ marginBottom: 16 }}>
                <h4 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>
                  🥚 {stepsData.dragon_name} — шаг {stepsData.current_step} из {stepsData.total}
                  <button className="lair-btn lair-btn-sm lair-btn-danger" style={{ marginLeft: 12 }}
                          onClick={() => resetProgress(detail.vk_id)}>🔄 Сбросить</button>
                </h4>
                <table className="lair-table">
                  <thead><tr><th style={{ width: 40 }}>#</th><th>Задание</th><th style={{ width: 60 }}>Статус</th><th style={{ width: 70 }}></th></tr></thead>
                  <tbody>
                    {stepsData.steps.map((s) => (
                      <tr key={s.step_number} style={{ background: s.current ? 'rgba(201,160,220,0.06)' : undefined }}>
                        <td style={{ fontWeight: s.current ? 700 : undefined }}>{s.step_number}{s.current ? ' ←' : ''}</td>
                        <td>
                          {s.magic_action && <div style={{ fontSize: 14 }}>✨ {s.magic_action}</div>}
                          <div style={{ fontSize: 14 }}>📝 {s.task_description}</div>
                          {s.hint && <div style={{ fontSize: 12, color: 'var(--parchment-faded)' }}>💡 {s.hint}</div>}
                        </td>
                        <td style={{ textAlign: 'center' }}>{s.completed ? '✅' : '→'}</td>
                        <td>
                          <button className="lair-btn lair-btn-sm lair-btn-outline"
                                  onClick={() => toggleStep(detail.vk_id, s.step_number)}>
                            {s.completed ? '↩ Отменить' : '✓ Выполнено'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="lair-card" style={{ marginBottom: 16 }}>
              <h4 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>Коллекция</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 6 }}>
                {detail.dragons.map((d) => (
                  <div key={d.dragon_id} className="lair-grid-cell" style={{ textAlign: 'center', padding: 12 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{d.name || d.egg_type}</div>
                    <div style={{ fontSize: 12, marginTop: 4 }}>{d.status === 'completed' ? '⭐' : d.status === 'growing' ? `${d.progress_pct}%` : '🔒'}</div>
                    <div style={{ display: 'flex', gap: 4, justifyContent: 'center', marginTop: 6 }}>
                      {d.status === 'completed' && (
                        <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ fontSize: 11 }}
                                onClick={() => restartDragon(detail.vk_id, d.dragon_id)}>🔄 Заново</button>
                      )}
                      <button className="lair-btn lair-btn-sm lair-btn-danger" style={{ fontSize: 11 }}
                              onClick={() => deleteDragon(detail.vk_id, d.dragon_id)}>✕ Удалить</button>
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
              <thead><tr><th>Игрок</th><th>Выращено</th><th>Текущий</th><th>Дата рег.</th><th style={{ width: 80 }}>Чат</th></tr></thead>
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
