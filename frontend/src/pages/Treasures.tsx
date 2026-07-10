import { useEffect, useState } from 'react';
import { useVkBridge } from '../context/VkBridgeContext';
import client from '../api/client';
import { mediaUrl } from '../api/media';

interface CollectedTreasure {
  id: number;
  name: string;
  description: string;
  image: string;
  dragon_id?: number;
  dragon_name?: string;
  family_id?: number;
  family_name?: string;
  source: string;
}

interface UncollectedTreasure {
  id: number;
  silhouette: string;
  source: string;
}

interface SectionData {
  collected: CollectedTreasure[];
  uncollected: UncollectedTreasure[];
}

interface TreasuresView {
  dragon: SectionData;
  family: SectionData;
  total: number;
}

type Tab = 'dragon' | 'family';

function Treasures() {
  const { vkUserId, loading: bl } = useVkBridge();
  const [data, setData] = useState<TreasuresView | null>(null);
  const [load, setLoad] = useState(true);
  const [zoom, setZoom] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('dragon');

  useEffect(() => {
    if (bl || !vkUserId) { setLoad(false); return; }
    client.get(`/collection/${vkUserId}/treasures`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoad(false));
  }, [vkUserId, bl]);

  if (bl || load) return <div style={{ padding: 40, textAlign: 'center' }}><div className="lair-skeleton" style={{ height: 200 }} /></div>;

  if (!data || data.total === 0) return (
    <div style={{ maxWidth: 420, margin: '40px auto', textAlign: 'center' }}>
      <div className="lair-card" style={{ padding: 28 }}>
        <div style={{ fontSize: 44, marginBottom: 10 }}>💎</div>
        <p style={{ color: 'var(--text-secondary)' }}>Сокровищ пока нет. Вырасти редкого дракона, чтобы получить сокровище.</p>
      </div>
    </div>
  );

  const section = data[tab];
  const collectedCount = section.collected.length;
  const totalCount = collectedCount + section.uncollected.length;
  const tabStyle = (t: Tab) => ({
    flex: 1,
    padding: '10px 16px',
    textAlign: 'center' as const,
    cursor: 'pointer',
    fontFamily: 'var(--font-title)',
    fontSize: 14,
    fontWeight: 600,
    letterSpacing: 1,
    textTransform: 'uppercase' as const,
    borderBottom: tab === t ? '2px solid var(--gold)' : '2px solid transparent',
    color: tab === t ? 'var(--gold)' : 'var(--parchment-dim)',
    transition: 'all 0.2s',
  });

  return (
    <div style={{ padding: '12px 10px', maxWidth: 640, margin: '0 auto' }}>
      <div className="lair-card" style={{ marginBottom: 12, textAlign: 'center' }}>
        <h2 style={{ color: 'var(--gold)', margin: '0 0 4px' }}>💎 Пещера сокровищ</h2>
        <div style={{ color: 'var(--parchment-dim)' }}>Собрано {data.dragon.collected.length + data.family.collected.length} из {data.total}</div>
      </div>

      <div style={{ display: 'flex', marginBottom: 12, borderRadius: 8, overflow: 'hidden', background: 'rgba(28,20,36,0.5)', border: '1px solid var(--bronze)' }}>
        <div style={tabStyle('dragon')} onClick={() => setTab('dragon')}>🐉 С драконов</div>
        <div style={tabStyle('family')} onClick={() => setTab('family')}>📂 С семейств</div>
      </div>

      {totalCount === 0 && (
        <div className="lair-card" style={{ textAlign: 'center', padding: 28 }}>
          <p style={{ color: 'var(--text-secondary)' }}>
            {tab === 'dragon' ? 'Сокровищ с драконов пока нет. Вырасти редкого дракона чтобы получить.' : 'Сокровищ с семейств пока нет. Собери всех драконов семейства чтобы получить.'}
          </p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12 }}>
        {section.collected.map((t) => (
          <div key={`c${t.id}`} className="lair-card" style={{ textAlign: 'center', padding: 12 }}>
            {t.image && (
              <img src={mediaUrl(t.image)} alt="" onClick={() => setZoom(mediaUrl(t.image))}
                   style={{ width: '100%', maxHeight: 140, objectFit: 'contain', borderRadius: 8, cursor: 'pointer' }}
                   onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
            )}
            <div style={{ color: 'var(--gold)', fontWeight: 600, marginTop: 8 }}>{t.name}</div>
            {t.description && <div style={{ fontSize: 13, color: 'var(--parchment-dim)', marginTop: 4 }}>{t.description}</div>}
            {t.dragon_name && <div style={{ fontSize: 12, color: 'var(--parchment-faded)', marginTop: 2 }}>{t.dragon_name}</div>}
            {t.family_name && <div style={{ fontSize: 12, color: 'var(--parchment-faded)', marginTop: 2 }}>{t.family_name}</div>}
          </div>
        ))}
        {section.uncollected.map((t) => (
          <div key={`u${t.id}`} className="lair-card" style={{ textAlign: 'center', padding: 12, opacity: 0.65 }}>
            <div style={{ position: 'relative' }}>
              {t.silhouette ? (
                <img src={mediaUrl(t.silhouette)} alt="" style={{ width: '100%', maxHeight: 140, objectFit: 'contain', borderRadius: 8, filter: 'brightness(0) opacity(0.55)' }} />
              ) : (
                <div style={{ height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 40 }}>💎</div>
              )}
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 40, color: 'var(--parchment-dim)' }}>?</div>
            </div>
          </div>
        ))}
      </div>

      {zoom && (
        <div onClick={() => setZoom(null)}
             style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          <img src={zoom} alt="" onClick={(e) => e.stopPropagation()}
               style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain', borderRadius: 8 }} />
          <button onClick={() => setZoom(null)}
                  style={{ position: 'absolute', top: 16, right: 16, background: 'none', border: 'none', color: '#fff', fontSize: 32, cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>
      )}
    </div>
  );
}

export default Treasures;
