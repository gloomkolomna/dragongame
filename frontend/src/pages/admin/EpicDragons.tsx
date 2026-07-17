import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Species { id: number; name: string; egg_type: string; rarity: number; is_epic: boolean; }

function EpicDragons() {
  const [species, setSpecies] = useState<Species[]>([]);
  const nav = useNavigate();

  useEffect(() => {
    client.get('/admin/epic/species').then((r) => setSpecies(r.data));
  }, []);

  return (
    <>
      <div className="lair-header"><h2>🐲 Эпические драконы</h2></div>
      <div className="lair-content">
        <div className="lair-card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
            <h4 style={{ color: 'var(--gold)', margin: 0 }}>Виды эпических ({species.length})</h4>
            <button className="lair-btn lair-btn-sm" style={{ marginLeft: 'auto' }}
                    onClick={() => nav('/admin/epic/species/new')}>+ Создать эпический вид</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
            {species.map((s) => (
              <div key={s.id} className="lair-grid-cell" style={{ padding: 12 }}>
                <div style={{ fontWeight: 600 }}>{s.name}</div>
                <div style={{ fontSize: 12, color: 'var(--parchment-dim)' }}>{s.egg_type || 'без типа яйца'}</div>
                <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
                  <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ flex: 1 }}
                          onClick={() => nav(`/admin/epic/species/${s.id}/edit`)}>Редактировать</button>
                  <button className="lair-btn lair-btn-sm" style={{ flex: 1 }}
                          onClick={() => nav(`/admin/epic/species/${s.id}/stages`)}>Этапы выращивания</button>
                </div>
              </div>
            ))}
            {species.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Пока нет эпических видов.</div>}
          </div>
        </div>
      </div>
    </>
  );
}

export default EpicDragons;
