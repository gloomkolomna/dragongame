import { useEffect, useState } from 'react';
import { useVkBridge } from '../context/VkBridgeContext';
import client from '../api/client';
import { mediaUrl } from '../api/media';

interface Moodlet {
  key: string;
  title: string;
  polarity?: string;
  text?: string;
  image_path?: string;
}

interface EpicView {
  has_epic: boolean;
  name?: string;
  egg_type?: string;
  egg_url?: string;
  dragon_url?: string;
  phase?: string;
  hatched?: boolean;
  egg_progress?: { completed: number; total: number };
  stage?: { number: number; name: string; description: string; image_start: string; image_end: string; cycle_completed: number; cycle_total: number };
  action?: { label: string; hint: string; crosses_norm: number; items: { id: number; name: string; owned: boolean }[] } | null;
  care_remaining_seconds?: number;
  moodlets?: Moodlet[];
  character?: { axis: string; label: string; polarity: string }[];
}

function fmtRemaining(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return `${h} ч. ${m} мин.`;
}

function Nest() {
  const { vkUserId, loading: bl } = useVkBridge();
  const [data, setData] = useState<EpicView | null>(null);
  const [load, setLoad] = useState(true);
  const [tab, setTab] = useState<'nest' | 'memories'>('nest');
  const [zoomMoodlet, setZoomMoodlet] = useState<Moodlet | null>(null);

  useEffect(() => {
    if (bl || !vkUserId) { setLoad(false); return; }
    client.get(`/collection/${vkUserId}/epic`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoad(false));
  }, [vkUserId, bl]);

  if (bl || load) return <div style={{ padding: 40, textAlign: 'center' }}><div className="lair-skeleton" style={{ height: 200 }} /></div>;

  if (!data || !data.has_epic) return (
    <div style={{ maxWidth: 420, margin: '40px auto', textAlign: 'center' }}>
      <div className="lair-card" style={{ padding: 28 }}>
        <div style={{ fontSize: 44, marginBottom: 10 }}>🕳️</div>
        <p style={{ color: 'var(--text-secondary)' }}>Гнездо пусто. Эпический дракон появится после того, как ты вырастишь своего первого дракона.</p>
      </div>
    </div>
  );

  const tabStyle = (t: string) => ({
    flex: 1,
    padding: '8px 16px',
    textAlign: 'center' as const,
    cursor: 'pointer',
    fontFamily: 'var(--font-title)',
    fontSize: 13,
    fontWeight: 600,
    letterSpacing: 1,
    textTransform: 'uppercase' as const,
    borderBottom: tab === t ? '2px solid var(--gold)' : '2px solid transparent',
    color: tab === t ? 'var(--gold)' : 'var(--parchment-dim)',
    transition: 'all 0.2s',
  });

  const img = data.dragon_url || data.egg_url;

  return (
    <div style={{ padding: '12px 10px', maxWidth: 560, margin: '0 auto' }}>
      {/* Sub-tabs: Гнездо / Воспоминания */}
      <div style={{ display: 'flex', marginBottom: 12, borderRadius: 8, overflow: 'hidden', background: 'rgba(28,20,36,0.5)', border: '1px solid var(--bronze)' }}>
        <div style={tabStyle('nest')} onClick={() => setTab('nest')}>🐲 Гнездо</div>
        <div style={tabStyle('memories')} onClick={() => setTab('memories')}>📔 Воспоминания</div>
      </div>

      {tab === 'nest' && (
        <>
          <div className="lair-card" style={{ marginBottom: 12, textAlign: 'center' }}>
            {img && <img src={mediaUrl(img)} alt="" style={{ maxWidth: 180, maxHeight: 180, objectFit: 'contain', borderRadius: 10 }} />}
            <h2 style={{ color: 'var(--gold)', margin: '10px 0 2px' }}>{data.name || data.egg_type || 'Эпический дракон'}</h2>
            {data.character && data.character.length > 0 && (
              <div style={{ fontSize: 14, color: 'var(--parchment-dim)', marginTop: 6 }}>
                🎭 {data.character.map((c, i) => (
                  <span key={i} style={{ color: c.polarity === 'positive' ? '#6fcf97' : '#d474a0' }}>
                    {c.label}{i < data.character!.length - 1 ? ', ' : ''}
                  </span>
                ))}
              </div>
            )}
          </div>

          {data.phase === 'egg' && data.egg_progress && (
            <div className="lair-card" style={{ marginBottom: 12 }}>
              <h4 style={{ color: 'var(--gold)', marginTop: 0 }}>🥚 Яйцо растёт</h4>
              <div>Шагов пройдено: {data.egg_progress.completed} из {data.egg_progress.total}</div>
              {data.hatched && <div style={{ color: 'var(--gold)', marginTop: 6 }}>Готово вылупиться — загляни в бота!</div>}
            </div>
          )}

          {data.phase === 'care' && data.stage && (
            <div className="lair-card" style={{ marginBottom: 12 }}>
              <h4 style={{ color: 'var(--gold)', marginTop: 0 }}>Стадия «{data.stage.name}»</h4>
              {data.stage.description && <div style={{ fontSize: 14, color: 'var(--parchment-dim)', marginBottom: 6 }}>{data.stage.description}</div>}
              <div>Цикл {(data.stage.cycle_completed ?? 0) + 1} из {data.stage.cycle_total}</div>
              {data.care_remaining_seconds && data.care_remaining_seconds > 0 ? (
                <div style={{ marginTop: 8, color: 'var(--parchment-dim)' }}>😴 Отдыхает, вернись через {fmtRemaining(data.care_remaining_seconds)}</div>
              ) : data.action ? (
                <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--bronze, #4a3a2a)' }}>
                  <div style={{ fontWeight: 600 }}>▶ {data.action.label}</div>
                  {data.action.hint && <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>💡 {data.action.hint}</div>}
                  <div style={{ fontSize: 13, marginTop: 4 }}>🎯 Норма: {data.action.crosses_norm}</div>
                  {data.action.items.length > 0 && (
                    <div style={{ marginTop: 6 }}>
                      Нужные товары: {data.action.items.map((it) => (
                        <span key={it.id} className="lair-badge" style={{ marginRight: 4, opacity: it.owned ? 1 : 0.5 }}>
                          {it.owned ? '✅' : '🔒'} {it.name}
                        </span>
                      ))}
                    </div>
                  )}
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>Забота — в боте.</div>
                </div>
              ) : null}
            </div>
          )}
        </>
      )}

      {tab === 'memories' && (
        <div className="lair-card" style={{ marginBottom: 12 }}>
          <h4 style={{ color: 'var(--gold)', marginTop: 0 }}>📔 Дневник воспоминаний</h4>
          {!data.moodlets || data.moodlets.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Воспоминаний пока нет.</div>
          ) : (
            (() => {
              const m = data.moodlets[data.moodlets.length - 1];
              return (
                <div
                  onClick={() => setZoomMoodlet(m)}
                  style={{
                    cursor: 'pointer',
                    borderRadius: 8,
                    overflow: 'hidden',
                    border: '2px solid var(--bronze)',
                    background: m.polarity === 'negative' ? 'rgba(212,116,160,0.08)' : 'rgba(111,207,151,0.06)',
                    textAlign: 'center',
                  }}
                >
                  {m.image_path ? (
                    <img src={mediaUrl(m.image_path)} alt={m.title} style={{ width: '100%', maxHeight: 260, objectFit: 'contain', display: 'block' }} />
                  ) : (
                    <div style={{ fontSize: 64, padding: 32 }}>{m.polarity === 'negative' ? '💔' : '🌟'}</div>
                  )}
                  <div style={{ padding: '10px 16px 14px' }}>
                    <div style={{ color: 'var(--gold)', fontWeight: 600, fontSize: 16 }}>{m.title}</div>
                    {m.text && <div style={{ color: 'var(--parchment-dim)', fontSize: 14, marginTop: 6 }}>{m.text}</div>}
                  </div>
                </div>
              );
            })()
          )}
        </div>
      )}

      {zoomMoodlet && (
        <div
          onClick={() => setZoomMoodlet(null)}
          style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, cursor: 'pointer' }}
        >
          <div className="lair-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 360, width: '100%', padding: 0, overflow: 'hidden', cursor: 'default', textAlign: 'center' }}>
            {zoomMoodlet.image_path ? (
              <img src={mediaUrl(zoomMoodlet.image_path)} alt={zoomMoodlet.title}
                   style={{ width: '100%', maxHeight: 340, objectFit: 'contain', display: 'block', background: 'rgba(0,0,0,0.3)' }} />
            ) : (
              <div style={{ fontSize: 64, padding: 32 }}>{zoomMoodlet.polarity === 'negative' ? '💔' : '🌟'}</div>
            )}
            <div style={{ padding: '16px 20px 20px' }}>
              <div style={{ color: 'var(--gold)', fontFamily: 'var(--font-title)', fontSize: 18, fontWeight: 700 }}>{zoomMoodlet.title}</div>
              {zoomMoodlet.text && (
                <div style={{ color: 'var(--parchment-dim)', fontSize: 15, marginTop: 10, lineHeight: 1.6 }}>{zoomMoodlet.text}</div>
              )}
            </div>
            <button onClick={() => setZoomMoodlet(null)}
                    style={{ position: 'absolute', top: 8, right: 8, width: 36, height: 36, borderRadius: '50%', border: '2px solid var(--bronze)', background: 'rgba(21,15,26,0.85)', color: 'var(--gold)', fontSize: 18, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1 }}>
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Nest;
