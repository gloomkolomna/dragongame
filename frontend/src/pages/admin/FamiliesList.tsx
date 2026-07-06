import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Family { id: number; name: string; description: string; sort_order: number; color: string; image_path: string; dragon_count: number; }

function FamiliesList() {
  const [families, setFamilies] = useState<Family[]>([]);
  const [load, setLoad] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    client.get('/admin/families').then((r) => setFamilies(r.data)).finally(() => setLoad(false));
  }, []);

  const del = async (id: number) => {
    if (!confirm('Удалить семейство / союз? Драконы останутся без него.')) return;
    await client.delete(`/admin/families/${id}`);
    setFamilies((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <>
      <div className="lair-header">
        <h2>📂 Семейства / Союзы</h2>
        <button className="lair-btn" style={{ marginLeft: 'auto' }} onClick={() => nav('/admin/families/new')}>+ Создать</button>
      </div>
      <div className="lair-content">
        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="lair-table">
            <thead><tr><th style={{ width: 40 }}></th><th>Название</th><th>Описание</th><th>Цвет</th><th>Порядок</th><th>Драконов</th><th style={{ width: 100 }}></th></tr></thead>
            <tbody>{families.map((f) => (
              <tr key={f.id}>
                <td><div style={{ width: 20, height: 20, borderRadius: 6, background: f.color || '#9b6fc7', border: '2px solid var(--bronze)' }} /></td>
                <td style={{ fontWeight: 600 }}>{f.name}</td>
                <td style={{ color: 'var(--parchment-dim)', fontSize: 14 }}>{f.description}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: 13 }}>{f.color || '#9b6fc7'}</td>
                <td>{f.sort_order}</td>
                <td>{f.dragon_count}</td>
                <td>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => nav(`/admin/families/${f.id}/edit`)}>✎</button>
                    <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => del(f.id)}>✕</button>
                  </div>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export default FamiliesList;
