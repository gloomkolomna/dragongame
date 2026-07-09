import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Species { id: number; name: string; egg_type: string; rarity: number; is_epic: boolean; }
interface Stage {
  id: number; stage_number: number; name: string; description: string;
  image_path: string; cycles_count: number;
}

function EpicDragons() {
  const [species, setSpecies] = useState<Species[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const nav = useNavigate();

  const reload = () => {
    client.get('/admin/epic/species').then((r) => setSpecies(r.data));
    client.get('/admin/epic/stages').then((r) => setStages(r.data));
  };
  useEffect(() => { reload(); }, []);

  const delStage = async (id: number) => {
    if (!window.confirm('Удалить стадию со всеми действиями и выборами?')) return;
    await client.delete(`/admin/epic/stages/${id}`);
    reload();
  };

  const persistOrder = async (list: Stage[]) => {
    await Promise.all(list.map((s, i) =>
      s.stage_number === i + 1 ? Promise.resolve() : client.put(`/admin/epic/stages/${s.id}`, { stage_number: i + 1 })
    ));
    reload();
  };
  const onDrop = (targetIdx: number) => {
    if (dragIdx === null || dragIdx === targetIdx) { setDragIdx(null); return; }
    const list = [...stages];
    const [moved] = list.splice(dragIdx, 1);
    list.splice(targetIdx, 0, moved);
    setStages(list);
    setDragIdx(null);
    persistOrder(list);
  };

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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8 }}>
            {species.map((s) => (
              <div key={s.id} className="lair-grid-cell" style={{ padding: 12 }}>
                <div style={{ fontWeight: 600 }}>{s.name}</div>
                <div style={{ fontSize: 12, color: 'var(--parchment-dim)' }}>{s.egg_type || 'без типа яйца'}</div>
                <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ marginTop: 8, width: '100%' }}
                        onClick={() => nav(`/admin/epic/species/${s.id}/edit`)}>Редактировать</button>
              </div>
            ))}
            {species.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Пока нет эпических видов.</div>}
          </div>
        </div>

        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--bronze)', display: 'flex', alignItems: 'center' }}>
            <h4 style={{ color: 'var(--gold)', margin: 0 }}>Этапы выращивания (общие)</h4>
            <button className="lair-btn lair-btn-sm" style={{ marginLeft: 'auto' }} onClick={() => nav('/admin/epic/stages/new')}>+ Стадия</button>
          </div>
          <table className="lair-table">
            <thead><tr><th style={{ width: 40 }}></th><th style={{ width: 40 }}>№</th><th>Название</th><th>Циклы</th><th style={{ width: 200 }}></th></tr></thead>
            <tbody>{stages.map((s, idx) => (
              <tr key={s.id}
                  draggable
                  onDragStart={() => setDragIdx(idx)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => onDrop(idx)}
                  style={{ opacity: dragIdx === idx ? 0.4 : 1 }}>
                <td style={{ cursor: 'grab', color: 'var(--parchment-faded)' }} title="Перетащить">⠿</td>
                <td>{s.stage_number}</td>
                <td style={{ fontWeight: 600 }}>{s.name}</td>
                <td>{s.cycles_count}</td>
                <td>
                  <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ marginRight: 4 }} onClick={() => nav(`/admin/epic/stages/${s.id}`)}>⚙ Действия ухода</button>
                  <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ marginRight: 4 }} onClick={() => nav(`/admin/epic/stages/${s.id}/edit`)}>Ред.</button>
                  <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => delStage(s.id)}>✕</button>
                </td>
              </tr>
            ))}
            {stages.length === 0 && <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16 }}>Стадий пока нет</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export default EpicDragons;
