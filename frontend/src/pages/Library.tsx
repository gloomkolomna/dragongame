import { useEffect, useState } from 'react';
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
  cover: string;
  name: string;
  fragments: LegendFrag[];
}

function Library() {
  const { vkUserId, loading: bl } = useVkBridge();
  const [items, setItems] = useState<LegendIndexItem[]>([]);
  const [load, setLoad] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<LegendView | null>(null);
  const [zoom, setZoom] = useState<string | null>(null);

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
      <div className="lair-card" style={{ marginBottom: 12, textAlign: 'center' }}>
        {detail.cover && (
          <img src={mediaUrl(detail.cover)} alt="" onClick={() => setZoom(mediaUrl(detail.cover))}
               style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 8, cursor: 'pointer' }}
               onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
        )}
        <h2 style={{ color: 'var(--gold)', margin: '10px 0 0' }}>{detail.name}</h2>
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
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 12 }}>
        {items.map((it) => (
          <div key={it.dragon_id} className="lair-card clickable" style={{ textAlign: 'center', padding: 12, cursor: 'pointer' }}
               onClick={() => setSelected(it.dragon_id)}>
            {it.cover ? (
              <img src={mediaUrl(it.cover)} alt="" style={{ width: '100%', maxHeight: 150, objectFit: 'contain', borderRadius: 8 }}
                   onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
            ) : (
              <div style={{ height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 40 }}>📖</div>
            )}
            <div style={{ color: 'var(--gold)', fontWeight: 600, marginTop: 8 }}>{it.name}</div>
            <div style={{ fontSize: 13, color: 'var(--parchment-dim)', marginTop: 4 }}>
              Открыто {it.fragments_opened} из {it.fragments_total}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Library;
