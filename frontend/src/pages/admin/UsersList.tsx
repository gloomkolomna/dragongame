import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import client from '../../api/client';
import { mediaUrl } from '../../api/media';

const GROUP_ID = 239999455;

interface User { vk_id: number; first_name: string; last_name: string; state: string; registered_at: string; pins_activated: number; last_pin_code: string | null; dragons_collected: number; current_dragon_id: number | null; current_step: number; suspicious_pending: number; }
interface Detail { vk_id: number; first_name: string; last_name: string; registered_at: string; stitches_balance: number; epic_unlocked: boolean; pins_activated: number; pins: { code: string; dragon_name: string; egg_type: string; status: string; activated_at: string }[]; dragons: { dragon_id: number; name: string | null; egg_type: string; status: string; progress_pct: number; completed_at: string | null }[]; dragons_collected: number; dragons_active: number; dragons_total: number; suspicious_reports: Suspicious[]; treasures_collected: TreasureCollected[]; }
interface TreasureCollected { id: number; name: string; description: string; image_path: string; dragon_id: number; is_active: boolean; }
interface Suspicious { id: number; user_id: number; dragon_id: number | null; step_number: number; declared_crosses: number; normal_crosses: number; mode: string; status: string; created_at: string; }

function UsersList() {
  const [users, setUsers] = useState<User[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [suspicious, setSuspicious] = useState<Suspicious[]>([]);
  const [balanceInput, setBalanceInput] = useState('');
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
    setBalanceInput(String(r.data.stitches_balance ?? 0));
    setSearchParams({ vk_id: String(id) });
    setSuspicious(r.data.suspicious_reports ?? []);
  };

  const saveBalance = async () => {
    if (!detail) return;
    const val = parseInt(balanceInput, 10);
    if (isNaN(val)) return;
    const r = await client.post(`/admin/users/${detail.vk_id}/balance`, { balance: val });
    setDetail({ ...detail, stitches_balance: r.data.stitches_balance });
  };

  const resolveSuspicious = async (reportId: number) => {
    if (!detail) return;
    if (!window.confirm('Пометить отчёт обработанным и удалить его?')) return;
    try {
      await client.delete(`/admin/suspicious/${reportId}`);
      setSuspicious((prev) => prev.filter((s) => s.id !== reportId));
      setUsers((prev) => prev.map((u) =>
        u.vk_id === detail.vk_id
          ? { ...u, suspicious_pending: Math.max(0, (u.suspicious_pending || 0) - 1) }
          : u));
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

  const deleteUser = async (vkId: number, name: string) => {
    const fullName = name || `id${vkId}`;
    if (!window.confirm(
      `Удалить игрока ${fullName} (id${vkId})?\n\n` +
      `Все драконы, прогресс, баланс, сокровища, эпик-слот будут удалены БЕЗВОЗВРАТНО.`
    )) return;
    const typed = window.prompt(
      `Для подтверждения введи VK ID игрока (${vkId}):`
    );
    if (typed === null) return;
    if (String(typed).trim() !== String(vkId)) {
      alert('Введённый ID не совпадает. Удаление отменено.');
      return;
    }
    try {
      await client.delete(`/admin/users/${vkId}`);
      setDetail(null);
      setSearchParams({});
      setUsers((prev) => prev.filter((u) => u.vk_id !== vkId));
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const profileUrl = (vkId: number) => `https://vk.com/id${vkId}`;
  const chatUrl = (vkId: number) => `https://vk.com/gim${GROUP_ID}?sel=${vkId}`;
  const convoUrl = (vkId: number) => `https://vk.com/gim${GROUP_ID}/convo/${vkId}`;

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
              <h4 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>✚ Копилка крестиков</h4>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input className="lair-input" type="text" inputMode="numeric" value={balanceInput}
                       onChange={(e) => setBalanceInput(e.target.value)} style={{ width: 160 }} />
                <button className="lair-btn lair-btn-sm" onClick={saveBalance}>💾 Установить баланс</button>
                {detail.epic_unlocked && <span className="lair-badge" style={{ marginLeft: 'auto' }}>🐲 эпический открыт</span>}
              </div>
            </div>

            <div className="lair-card" style={{ marginBottom: 16 }}>
              <h4 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>⚠ Подозрительные отчёты ({suspicious.length})</h4>
              {suspicious.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Нет подозрительных отчётов</div>
              ) : (
                <table className="lair-table">
                  <thead><tr><th>Дата</th><th>Шаг</th><th>Заявлено</th><th>Норма</th><th>Режим</th><th></th></tr></thead>
                  <tbody>{suspicious.map((s) => (
                    <tr key={s.id}>
                      <td style={{ fontSize: 13 }}>{s.created_at?.slice(0, 16).replace('T', ' ')}</td>
                      <td>{s.step_number}</td>
                      <td style={{ color: '#d474a0', fontWeight: 600 }}>{s.declared_crosses}</td>
                      <td>{s.normal_crosses}</td>
                      <td>{s.mode}</td>
                      <td style={{ display: 'flex', gap: 4 }}>
                        <a href={convoUrl(detail.vk_id)} target="_blank" rel="noopener noreferrer" className="lair-btn lair-btn-sm lair-btn-outline" style={{ textDecoration: 'none' }}>💬 В чат</a>
                        <button className="lair-btn lair-btn-sm" onClick={() => resolveSuspicious(s.id)}>✔ Обработано</button>
                      </td>
                    </tr>
                  ))}</tbody>
                </table>
              )}
            </div>

            <div className="lair-card" style={{ marginBottom: 16 }}>
              <h4 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>💎 Сокровища ({detail.treasures_collected?.length || 0})</h4>
              {(detail.treasures_collected?.length || 0) === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Игрок пока не собрал сокровищ</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8 }}>
                  {detail.treasures_collected.map((tr) => (
                    <div key={tr.id} className="lair-grid-cell" style={{ textAlign: 'center', padding: 8 }}>
                      {tr.image_path ? (
                        <img src={mediaUrl(tr.image_path)} alt={tr.name} style={{ width: '100%', maxHeight: 80, objectFit: 'contain', borderRadius: 6 }} />
                      ) : (
                        <div style={{ fontSize: 28, lineHeight: '80px' }}>💎</div>
                      )}
                      <div style={{ fontSize: 12, marginTop: 4 }}>{tr.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>от дракона #{tr.dragon_id}</div>
                    </div>
                  ))}
                </div>
              )}
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
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, width: '100%' }}>
                        {d.status === 'completed' && (
                          <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ fontSize: 11, width: '100%', boxSizing: 'border-box', whiteSpace: 'nowrap' }}
                                  onClick={() => restartDragon(detail.vk_id, d.dragon_id)}>🔄 Заново</button>
                        )}
                        <button className="lair-btn lair-btn-sm lair-btn-danger" style={{ fontSize: 11, width: '100%', boxSizing: 'border-box', whiteSpace: 'nowrap' }}
                                onClick={() => deleteDragon(detail.vk_id, d.dragon_id)}>✕ Удалить</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="lair-card" style={{ marginBottom: 16, borderColor: 'var(--danger-bg)' }}>
              <h4 style={{ color: '#d47474', margin: '0 0 12px' }}>⚠ Опасная зона</h4>
              <button className="lair-btn lair-btn-danger"
                      onClick={() => deleteUser(
                        detail.vk_id,
                        [detail.first_name, detail.last_name].filter(Boolean).join(' ')
                      )}>
                🗑 Удалить игрока
              </button>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Игрок и весь его прогресс будут удалены безвозвратно. Логи сохранятся.
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
                      {u.suspicious_pending > 0 && (
                        <span style={{
                          marginLeft: 8, padding: '1px 7px', borderRadius: 10,
                          background: '#d474a0', color: '#fff', fontSize: 12, fontWeight: 700,
                          whiteSpace: 'nowrap',
                        }} title="Подозрительные отчёты на проверку">
                          ⚠ {u.suspicious_pending}
                        </span>
                      )}
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
