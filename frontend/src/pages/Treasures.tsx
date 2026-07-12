import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
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

const PER_PAGE = 9;
const COLS = 3;
const ROWS = 3;

function Treasures() {
  const { vkUserId, loading: bl } = useVkBridge();
  const [data, setData] = useState<TreasuresView | null>(null);
  const [load, setLoad] = useState(true);
  const [detail, setDetail] = useState<CollectedTreasure | null>(null);
  const [zoomImg, setZoomImg] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('dragon');
  const [page, setPage] = useState(0);
  const nav = useNavigate();
  const [params] = useSearchParams();

  useEffect(() => {
    if (bl || !vkUserId) { setLoad(false); return; }
    client.get(`/collection/${vkUserId}/treasures`)
      .then((r) => {
        setData(r.data);
        const tid = params.get('treasure');
        if (tid) {
          const all = [...r.data.dragon.collected, ...r.data.family.collected];
          const found = all.find((t: CollectedTreasure) => t.id === Number(tid));
          if (found) {
            setTab(found.source === 'family' ? 'family' : 'dragon');
            setDetail(found);
          }
        }
      })
      .catch(() => setData(null))
      .finally(() => setLoad(false));
  }, [vkUserId, bl]);

  useEffect(() => {
    setPage(0);
  }, [tab]);

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

  const allItems: ({ type: 'collected' } & CollectedTreasure | { type: 'uncollected' } & UncollectedTreasure)[] = [
    ...section.collected.map((t) => ({ ...t, type: 'collected' as const })),
    ...section.uncollected.map((t) => ({ ...t, type: 'uncollected' as const })),
  ];
  const totalPages = Math.max(1, Math.ceil(allItems.length / PER_PAGE));
  const start = page * PER_PAGE;
  const pageItems = allItems.slice(start, start + PER_PAGE);

  return (
    <div style={{ padding: '12px 10px', maxWidth: 640, margin: '0 auto' }}>
      <div className="lair-card" style={{ marginBottom: 12, textAlign: 'center' }}>
        <h2 style={{ color: 'var(--gold)', margin: '0 0 4px' }}>💎 Пещера сокровищ</h2>
        <div style={{ color: 'var(--parchment-dim)' }}>Собрано {data.dragon.collected.length + data.family.collected.length} из {data.total}</div>
      </div>

      <div style={{ display: 'flex', marginBottom: 12, borderRadius: 8, overflow: 'hidden', background: 'rgba(28,20,36,0.5)', border: '1px solid var(--bronze)' }}>
        <div style={tabStyle('dragon')} onClick={() => setTab('dragon')}>🐲 С драконов</div>
        <div style={tabStyle('family')} onClick={() => setTab('family')}>📂 С семейств</div>
      </div>

      {totalCount === 0 && (
        <div className="lair-card" style={{ textAlign: 'center', padding: 28 }}>
          <p style={{ color: 'var(--text-secondary)' }}>
            {tab === 'dragon' ? 'Сокровищ с драконов пока нет. Вырасти редкого дракона чтобы получить.' : 'Сокровищ с семейств пока нет. Собери всех драконов семейства чтобы получить.'}
          </p>
        </div>
      )}

      {totalCount > 0 && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${COLS}, 1fr)`, gap: 8 }}>
            {pageItems.map((t) => {
              if (t.type === 'collected') {
                return (
                  <div key={`c${t.id}`} className="lair-grid-cell" onClick={() => setDetail(t)}
                       style={{ position: 'relative', overflow: 'hidden', cursor: 'pointer', padding: 0, minHeight: 160, border: '2px solid var(--bronze)', background: 'var(--bg-card)' }}>
                    {t.image && (
                      <img src={mediaUrl(t.image)} alt=""
                           style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', inset: 0 }}
                           onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                    )}
                    <div style={{
                      position: 'absolute', bottom: 0, left: 0, right: 0,
                      padding: '5px 8px', background: 'rgba(21,15,26,0.78)',
                      fontSize: 14, color: 'var(--gold)', textAlign: 'center',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 600,
                    }}>
                      {t.name}
                    </div>
                  </div>
                );
              }
              return (
                <div key={`u${t.id}`} className="lair-grid-cell"
                     style={{ position: 'relative', overflow: 'hidden', padding: 0, minHeight: 160, border: '2px solid var(--bronze)', background: 'var(--bg-card)', opacity: 0.65 }}>
                  <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 160 }}>
                    {t.silhouette ? (
                      <img src={mediaUrl(t.silhouette)} alt=""
                           style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', inset: 0, filter: 'brightness(0) opacity(0.55)' }} />
                    ) : (
                      <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 40 }}>💎</div>
                    )}
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 40, color: 'var(--parchment-dim)' }}>?</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 16 }}>
              <button
                className="lair-btn lair-btn-sm"
                disabled={page === 0}
                onClick={() => setPage(page - 1)}
                style={{ opacity: page === 0 ? 0.4 : 1 }}
              >
                ← Назад
              </button>
              <span style={{ color: 'var(--parchment-dim)', fontSize: 14 }}>
                {page + 1} / {totalPages}
              </span>
              <button
                className="lair-btn lair-btn-sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage(page + 1)}
                style={{ opacity: page >= totalPages - 1 ? 0.4 : 1 }}
              >
                Вперёд →
              </button>
            </div>
          )}
        </>
      )}

      {detail && (
        <div onClick={() => setDetail(null)}
             style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, cursor: 'pointer' }}>
          <div className="lair-card" onClick={(e) => e.stopPropagation()}
               style={{ maxWidth: 400, width: '100%', padding: 0, overflow: 'hidden', cursor: 'default' }}>
            <div style={{ position: 'relative' }}>
              {detail.image && (
                <img src={mediaUrl(detail.image)} alt="" onClick={(e) => { e.stopPropagation(); setZoomImg(mediaUrl(detail.image)); }}
                     style={{ width: '100%', maxHeight: 320, objectFit: 'contain', display: 'block', borderTopLeftRadius: 24, borderTopRightRadius: 24, background: 'rgba(0,0,0,0.3)', cursor: 'pointer' }} />
              )}
              <button onClick={() => setDetail(null)}
                      style={{ position: 'absolute', top: 8, right: 8, width: 36, height: 36, borderRadius: '50%', border: '2px solid var(--bronze)', background: 'rgba(21,15,26,0.85)', color: 'var(--gold)', fontSize: 18, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1 }}>
                ✕
              </button>
            </div>
            <div style={{ padding: '20px 20px 24px' }}>
              <div style={{ color: 'var(--gold)', fontFamily: 'var(--font-title)', fontSize: 20, fontWeight: 700, letterSpacing: 0.5 }}>{detail.name}</div>
              {detail.dragon_name && detail.dragon_id && (
                <div onClick={() => { setDetail(null); nav(`/dragon/${detail.dragon_id}`); }}
                     style={{ color: 'var(--fire)', fontSize: 14, marginTop: 4, cursor: 'pointer', textDecoration: 'underline' }}>
                  🐲 {detail.dragon_name}
                </div>
              )}
              {detail.family_name && (
                <div style={{ color: 'var(--parchment-faded)', fontSize: 14, marginTop: 4 }}>📂 {detail.family_name}</div>
              )}
              {detail.description && (
                <div style={{ color: 'var(--parchment-dim)', fontSize: 15, marginTop: 14, lineHeight: 1.6, borderTop: '1px solid var(--bronze)', paddingTop: 14 }}>{detail.description}</div>
              )}
            </div>
          </div>
        </div>
      )}

      {zoomImg && (
        <div onClick={() => setZoomImg(null)}
             style={{ position: 'fixed', inset: 0, zIndex: 1100, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          <img src={zoomImg} alt="" onClick={(e) => e.stopPropagation()}
               style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain', borderRadius: 8, boxShadow: '0 0 60px rgba(153,102,255,0.3)' }} />
          <button onClick={() => setZoomImg(null)}
                  style={{ position: 'absolute', top: 16, right: 16, background: 'none', border: 'none', color: '#fff', fontSize: 32, cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>
      )}
    </div>
  );
}

export default Treasures;
