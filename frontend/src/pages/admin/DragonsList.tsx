import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Dragon { id: number; name: string; rarity: number; egg_type: string; steps_count: number; is_active: boolean; }

const RARITY = ['', 'Обычный', 'Редкий', 'Эпический', 'Легендарный'];

function DragonsList() {
  const [dragons, setDragons] = useState<Dragon[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetch = () => { setLoading(true); client.get('/admin/dragons').then((r) => setDragons(r.data)).finally(() => setLoading(false)); };
  useEffect(fetch, []);

  const remove = async (id: number, name: string) => {
    if (!window.confirm(`Удалить «${name}» и все связанные данные?`)) return;
    await client.delete(`/admin/dragons/${id}`); fetch();
  };

  return (
    <>
      <div className="lair-header">
        <h2>Драконы</h2>
        <button className="lair-btn" onClick={() => navigate('/admin/dragons/new')}>+ Создать</button>
      </div>
      <div className="lair-content">
        {loading ? <div className="dragon-skeleton-card" style={{ height: 300 }} /> : (
          <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="lair-table">
              <thead><tr><th>ID</th><th>Имя</th><th>Редкость</th><th>Яйцо</th><th>Шагов</th><th>Акт.</th><th style={{ width: 170 }}>Действия</th></tr></thead>
              <tbody>
                {dragons.map((d) => (
                  <tr key={d.id}>
                    <td>{d.id}</td>
                    <td style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/dragons/${d.id}/edit`)}>{d.name}</td>
                    <td><span className="dragon-badge lair-badge-common">{RARITY[d.rarity]}</span></td>
                    <td>{d.egg_type}</td>
                    <td><span style={{ color: 'var(--accent-gold-light)', fontWeight: 600 }}>{d.steps_count}</span></td>
                    <td>{d.is_active ? '✅' : '❌'}</td>
                    <td>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => navigate(`/admin/dragons/${d.id}/steps`)} style={{ marginRight: 4 }}>📝 Шаги</button>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => navigate(`/admin/dragons/${d.id}/edit`)} style={{ marginRight: 4 }}>Ред.</button>
                      <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => remove(d.id, d.name)}>Уд.</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <style>{`.dragon-skeleton-card{height:300px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:shimmer 1.5s infinite}@keyframes shimmer{0%{opacity:.4}50%{opacity:.7}100%{opacity:.4}}`}</style>
    </>
  );
}

export default DragonsList;
