import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Stage { id: number; dragon_id: number; stage_number: number; name: string; }
interface Action { id: number; dragon_id: number; stage_id: number; action_label: string; order_in_cycle: number; task: string; hint: string; crosses_norm: number; image_path: string; action_type: string; timeout_hours: number; timeout_minutes: number; item_ids: number[]; sub_actions?: { id: number; label: string; order_in_sub: number }[]; }
interface Species { id: number; name: string; }

function EpicStageEditor() {
  const { stageId } = useParams<{ stageId: string }>();
  const sid = Number(stageId);
  const nav = useNavigate();
  const [stage, setStage] = useState<Stage | null>(null);
  const [actions, setActions] = useState<Action[]>([]);
  const [species, setSpecies] = useState<Species[]>([]);
  const [did, setDid] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [rows, setRows] = useState<Action[]>([]);
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  const [label, setLabel] = useState('');
  const [actionType, setActionType] = useState('simple');

  const loadActions = () => {
    if (!did) { setActions([]); return Promise.resolve(); }
    return client.get(`/admin/epic/species/${did}/stages/${sid}/actions`).then((r) => setActions(r.data));
  };

  useEffect(() => {
    client.get('/admin/epic/stages').then((r) => {
      const s = r.data.find((x: Stage) => x.id === sid) || null;
      setStage(s);
      if (s) setDid(s.dragon_id);
    });
    client.get('/admin/epic/species').then((r) => setSpecies(r.data));
  }, [sid]);

  useEffect(() => { loadActions(); }, [sid, did]);
  useEffect(() => { setRows(actions); }, [actions]);

  const nextOrder = (rows.length ? Math.max(...rows.map((a) => a.order_in_cycle)) : 0) + 1;

  const add = async () => {
    if (!label.trim()) { setError('Впиши название'); return; }
    if (!did) { setError('Выбери эпического дракона'); return; }
    setError('');
    const r = await client.post(`/admin/epic/species/${did}/stages/${sid}/actions`, {
      action_label: label, action_type: actionType, order_in_cycle: nextOrder, crosses_norm: 1000, timeout_hours: 0, timeout_minutes: 0,
    });
    setLabel(''); setActionType('simple');
    loadActions();
    if (r.data.id) nav(`/admin/epic/stages/${sid}/actions/${r.data.id}`);
  };

  const del = async (id: number) => {
    if (!confirm('Удалить действие?')) return;
    await client.delete(`/admin/epic/actions/${id}`);
    loadActions();
  };

  const persistOrder = async (list: Action[]) => {
    await Promise.all(list.map((a, i) =>
      a.order_in_cycle === i + 1 ? Promise.resolve() : client.put(`/admin/epic/actions/${a.id}`, { order_in_cycle: i + 1 })
    ));
    loadActions();
  };

  const onDrop = (targetIdx: number) => {
    if (dragIdx === null || dragIdx === targetIdx) { setDragIdx(null); return; }
    const list = [...rows];
    const [moved] = list.splice(dragIdx, 1);
    list.splice(targetIdx, 0, moved);
    setRows(list);
    setDragIdx(null);
    persistOrder(list);
  };

  return (
    <>
      <div className="lair-header">
        <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => nav('/admin/epic')}>← Назад</button>
        <h2 style={{ marginLeft: 12 }}>⚙ {stage ? `Стадия ${stage.stage_number}: ${stage.name}` : 'Стадия'}</h2>
        <button className="lair-btn lair-btn-outline lair-btn-sm" style={{ marginLeft: 'auto' }}
                onClick={() => nav(`/admin/epic/stages/${sid}/edit`)}>✎ Редактировать этап</button>
      </div>
      <div className="lair-content">
        {error && <div style={{ padding: '8px 12px', marginBottom: 12, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        <div className="lair-card" style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <label className="lair-label" style={{ margin: 0 }}>Эпический дракон:</label>
          <span style={{ fontWeight: 600, color: 'var(--gold)' }}>{species.find((s) => s.id === did)?.name || '—'}</span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Стадия и действия уникальны для этого дракона</span>
        </div>
        {!did ? (
          <div className="lair-card" style={{ color: 'var(--text-muted)', fontSize: 14 }}>Стадия не найдена.</div>
        ) : (
          <ActionsList did={did} sid={sid} rows={rows} actions={actions} dragIdx={dragIdx} setDragIdx={setDragIdx}
                        onDrop={onDrop} nav={nav} del={del} nextOrder={nextOrder}
                        label={label} setLabel={setLabel} actionType={actionType}
                        setActionType={setActionType} add={add} />
        )}
      </div>
    </>
  );
}

function ActionsList({ did, sid, rows, actions, dragIdx, setDragIdx, onDrop, nav, del, nextOrder, label, setLabel, actionType, setActionType, add }: any) {
  const [items, setItems] = useState<{ id: number; name: string }[]>([]);
  useEffect(() => { client.get('/admin/shop-items').then((r) => setItems(r.data)); }, []);

  const itemName = (id: number) => items.find((i: any) => i.id === id)?.name || `#${id}`;

  return (
    <div className="lair-card">
      <h4 style={{ color: 'var(--gold)', margin: '0 0 4px' }}>Действия ухода (цикл)</h4>
      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
        Действия выполняются по порядку (перетаскивание ⠿). Нажми ✎ для полной настройки.
      </div>

      {rows.map((a: any, idx: number) => (
        <div key={a.id}
             draggable
             onDragStart={() => setDragIdx(idx)}
             onDragOver={(e) => e.preventDefault()}
             onDrop={() => onDrop(idx)}
             style={{ padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', opacity: dragIdx === idx ? 0.4 : 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ cursor: 'grab', color: 'var(--parchment-faded)' }} title="Перетащить">⠿</span>
            <span style={{ color: 'var(--gold)', width: 28, fontSize: 13 }}>#{a.order_in_cycle}</span>
            <span style={{ fontWeight: 600, minWidth: 120, fontSize: 14 }}>{a.action_label}</span>
            {(a.action_type === 'composite' || (a.sub_actions && a.sub_actions.length > 0)) ? (
              <span className="lair-badge" style={{ background: 'rgba(255,200,50,0.2)', color: '#ffc832', fontSize: 11 }}>составное ({a.sub_actions?.length || 0} вар.)</span>
            ) : a.item_ids && a.item_ids.length > 0 ? (
              <span style={{ color: 'var(--parchment-dim)', fontSize: 12 }}>
                📦 {a.item_ids.map(itemName).join(', ')}
              </span>
            ) : (
              <span style={{ color: 'var(--gold)', fontSize: 12 }}>{a.crosses_norm} ✚</span>
            )}
            <span style={{ color: 'var(--parchment-faded)', fontSize: 12 }}>
              ⏳ {a.timeout_hours ?? 0}ч {a.timeout_minutes ?? 0}м
            </span>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
              <button className="lair-btn lair-btn-sm lair-btn-outline"
                      onClick={() => nav(`/admin/epic/stages/${sid}/actions/${a.id}`)}>✎</button>
              <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => del(a.id)}>✕</button>
            </div>
          </div>
        </div>
      ))}

      <div style={{ borderTop: '1px solid var(--bronze)', paddingTop: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 600, color: 'var(--accent-gold-light)', marginBottom: 8 }}>Добавить действие (порядок #{nextOrder})</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}>
            <input className="lair-input" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Название действия" />
          </div>
          <div style={{ width: 170 }}>
            <select className="lair-input" value={actionType} onChange={(e) => setActionType(e.target.value)}>
              <option value="simple">Простое</option>
              <option value="composite">Составное</option>
            </select>
          </div>
          <button className="lair-btn" onClick={add}>+ Добавить</button>
        </div>
      </div>
    </div>
  );
}

export default EpicStageEditor;
