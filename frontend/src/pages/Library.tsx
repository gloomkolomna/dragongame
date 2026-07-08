import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useVkBridge } from '../context/VkBridgeContext';
import client from '../api/client';
import { mediaUrl } from '../api/media';

interface LegendIndexItem {
  dragon_id: number;
  name: string;
  cover: string;
  fragments_opened: number;
  fragments_total: number;
}

interface LegendFrag {
  number: number;
  opened: boolean;
  task: string;
  assignment: string;
  image: string;
}

interface LegendView {
  has_legend: boolean;
  dragon_id: number;
  cover: string;
  name: string;
  all_completed: boolean;
  full_text: string;
  fragments: LegendFrag[];
}

function Library() {
  const { vkUserId, loading: bl } = useVkBridge();
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<LegendIndexItem[]>([]);
  const [load, setLoad] = useState(true);
  const [detail, setDetail] = useState<LegendView | null>(null);
  const [zoom, setZoom] = useState<string | null>(null);

  const selected = params.get('dragon') ? Number(params.get('dragon')) : null;
  const setSelected = (id: number | null) => {
    if (id == null) { params.delete('dragon'); }
    else { params.set('dragon', String(id)); }
    setParams(params, { replace: true });
  };

  useEffect(() => {
    if (bl || !vkUserId) { setLoad(false); return; }
    client.get(`/collection/${vkUserId}/legends`)
      .then((r) => setItems(r.data))
      .catch(() => setItems([]))
      .finally(() => setLoad(false));
  }, [vkUserId, bl]);

  useEffect(() => {
    if (!vkUserId || selected == null) { setDetail(null); return; }
    client.get(`/collection/${vkUserId}/legend/${selected}`)
      .then((r) => setDetail(r.data))
      .catch(() => setDetail(null));
  }, [selected, vkUserId]);

  if (bl || load) return <div style={{ padding: 40, textAlign: 'center' }}><div className="lair-skeleton" style={{ height: 200 }} /></div>;

  if (selected != null && detail) return (
    <div style={{ padding: '12px 10px', maxWidth: 640, margin: '0 auto' }}>
      <button className="lair-btn lair-btn-outline lair-btn-sm" style={{ marginBottom: 12 }} onClick={() => setSelected(null)}>← К Библиотеке</button>
      <div className="lair-card lair-rise" style={{ marginBottom: 12, textAlign: 'center' }}>
        {detail.cover && (
          <img src={mediaUrl(detail.cover)} alt="" onClick={() => setZoom(mediaUrl(detail.cover))}
               style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 'var(--radius-md)', cursor: 'pointer' }}
               onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
        )}
        <h2 style={{ color: 'var(--gold)', margin: '10px 0 0', fontSize: 26, fontWeight: 700 }}>{detail.name}</h2>
        {detail.all_completed && detail.full_text && (
          <p style={{ color: 'var(--text-secondary)', fontSize: 17, lineHeight: 1.6, marginTop: 12, whiteSpace: 'pre-line', textAlign: 'left' }}>{detail.full_text}</p>
        )}
        <button className="lair-btn" style={{ width: '100%', marginTop: 14 }} onClick={() => nav(`/dragon/${detail.dragon_id}`)}>
          🐉 К дракону
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {detail.fragments.map((f) => (
          <div key={f.number} className="lair-card" style={{ padding: 12, background: f.opened ? 'var(--success-bg)' : 'var(--bg-card)' }}>
            {f.opened ? (
              <>
                {f.image && <img src={mediaUrl(f.image)} alt="" onClick={() => setZoom(mediaUrl(f.image))}
                     style={{ maxWidth: '100%', maxHeight: 180, borderRadius: 6, cursor: 'pointer', marginBottom: 6 }}
                     onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />}
                <div style={{ fontSize: 15 }}>{f.task}</div>
                {f.assignment && <div style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 6 }}>📋 {f.assignment}</div>}
              </>
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>🔒 Отрывок {f.number} ещё не открыт</div>
            )}
          </div>
        ))}
      </div>
      {zoom && (
        <div onClick={() => setZoom(null)}
             style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          <img src={zoom} alt="" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain', borderRadius: 8 }} />
          <button onClick={() => setZoom(null)} style={{ position: 'absolute', top: 16, right: 16, background: 'none', border: 'none', color: '#fff', fontSize: 32, cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>
      )}
    </div>
  );

  if (items.length === 0) return (
    <div style={{ maxWidth: 420, margin: '40px auto', textAlign: 'center' }}>
      <div className="lair-card" style={{ padding: 28 }}>
        <div style={{ fontSize: 44, marginBottom: 10 }}>📖</div>
        <p style={{ color: 'var(--text-secondary)' }}>В Библиотеке пока нет легенд.</p>
      </div>
    </div>
  );

  return (
    <div style={{ padding: '12px 10px', maxWidth: 640, margin: '0 auto' }}>
      <div className="lair-card" style={{ marginBottom: 12, textAlign: 'center' }}>
        <h2 style={{ color: 'var(--gold)', margin: 0 }}>📖 Библиотека легенд</h2>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 4 }}>
        {items.map((it) => (
          <div key={it.dragon_id} className="lair-grid-cell" onClick={() => setSelected(it.dragon_id)}
               title={it.name}
               style={{
                 aspectRatio: '1 / 1', padding: 0, overflow: 'hidden', cursor: 'pointer',
                 display: 'flex', alignItems: 'center', justifyContent: 'center',
                 background: 'var(--success-bg)', borderColor: 'rgba(58,138,101,0.4)',
               }}>
            <div style={{ width: '100%', height: '100%', position: 'relative' }}>
              {it.cover ? (
                <img src={mediaUrl(it.cover)} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                     onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
              ) : (
                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 44 }}>📖</div>
              )}
              <div style={{
                position: 'absolute', bottom: 0, left: 0, right: 0,
                padding: '4px 6px', background: 'rgba(21,15,26,0.78)',
                fontSize: 18, color: 'var(--gold)', textAlign: 'center',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 600,
              }}>
                {it.name}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Library;
