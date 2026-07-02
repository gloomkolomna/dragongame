import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Family { id: number; name: string; description: string; sort_order: number; dragon_count: number; }

function FamiliesList() {
  const [families, setFamilies] = useState<Family[]>([]);
  const [load, setLoad] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    client.get('/admin/families').then((r) => setFamilies(r.data)).finally(() => setLoad(false));
  }, []);

  const del = async (id: number) => {
    if (!confirm('Удалить семейство? Драконы останутся без семейства.')) return;
    await client.delete(`/admin/families/${id}`);
    setFamilies((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <>
      <div className="lair-header">
        <h2>📂 Семейства</h2>
        <button className="lair-btn" style={{ marginLeft: 'auto' }} onClick={() => nav('/admin/families/new')}>+ Создать</button>
      </div>
      <div className="lair-content">
        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="lair-table">
            <thead><tr><th>Название</th><th>Описание</th><th>Порядок</th><th>Драконов</th><th style={{ width: 100 }}></th></tr></thead>
            <tbody>{families.map((f) => (
              <tr key={f.id}>
                <td style={{ fontWeight: 600 }}>{f.name}</td>
                <td style={{ color: 'var(--parchment-dim)', fontSize: 13 }}>{f.description}</td>
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
