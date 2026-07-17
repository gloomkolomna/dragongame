import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Species { id: number; name: string; egg_type: string; rarity: number; is_epic: boolean; }
interface Stage {
  id: number; stage_number: number; name: string; description: string;
  image_path: string;
}

function EpicStagesList() {
  const { dragonId } = useParams();
  const navigate = useNavigate();
  const [dragon, setDragon] = useState<Species | null>(null);
  const [stages, setStages] = useState<Stage[]>([]);
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  const loadStages = (did: number) => {
    client.get('/admin/epic/stages', { params: { dragon_id: did } }).then((r) => setStages(r.data));
  };

  useEffect(() => {
    if (!dragonId) return;
    client.get('/admin/epic/species').then((r) => {
      const found = r.data.find((s: Species) => s.id === Number(dragonId));
      setDragon(found ?? null);
    });
    loadStages(Number(dragonId));
  }, [dragonId]);

  const delStage = async (id: number) => {
    if (!window.confirm('Удалить стадию со всеми действиями?')) return;
    await client.delete(`/admin/epic/stages/${id}`);
    loadStages(Number(dragonId));
  };

  const persistOrder = async (list: Stage[]) => {
    await Promise.all(list.map((s, i) =>
      s.stage_number === i + 1 ? Promise.resolve() : client.put(`/admin/epic/stages/${s.id}`, { stage_number: i + 1 })
    ));
    loadStages(Number(dragonId));
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
      <div className="lair-header">
        <h2>{dragon ? `🗂 Этапы: ${dragon.name}` : '🗂 Этапы выращивания'}</h2>
      </div>
      <div className="lair-content">
        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--bronze)', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => navigate('/admin/epic')}>← К эпическим</button>
            <button className="lair-btn lair-btn-sm" style={{ marginLeft: 'auto' }} disabled={!dragonId}
                    onClick={() => navigate(`/admin/epic/species/${dragonId}/stages/new`)}>+ Стадия</button>
          </div>
          <table className="lair-table">
            <thead><tr><th style={{ width: 40 }}></th><th style={{ width: 40 }}>№</th><th>Название</th><th style={{ width: 240 }}></th></tr></thead>
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
                <td>
                  <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ marginRight: 4 }} onClick={() => navigate(`/admin/epic/stages/${s.id}`)}>⚙ Действия ухода</button>
                  <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ marginRight: 4 }} onClick={() => navigate(`/admin/epic/stages/${s.id}/edit`)}>Ред.</button>
                  <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => delStage(s.id)}>✕</button>
                </td>
              </tr>
            ))}
            {stages.length === 0 && <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16 }}>Стадий пока нет</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export default EpicStagesList;
