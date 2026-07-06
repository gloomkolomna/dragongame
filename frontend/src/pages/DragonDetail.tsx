import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useVkBridge } from '../context/VkBridgeContext';
import client from '../api/client';
import { mediaUrl } from '../api/media';

interface Step { number: number; task: string; completed: boolean; }
interface Dragon { is_revealed: boolean; name?: string; rarity?: number; egg_type: string; steps_count: number; description?: string; dragon_url?: string; egg_url?: string; next_step_available_at?: string; family_color?: string; user_progress: { status: string; completed_steps: number; steps: Step[] }; }

function DragonDetail() {
  const { id } = useParams<{ id: string }>();
  const { vkUserId, loading: bl } = useVkBridge();
  const [d, setD] = useState<Dragon | null>(null);
  const [load, setLoad] = useState(true);
  const [zoom, setZoom] = useState<string | null>(null);
  const nav = useNavigate();

  useEffect(() => { if (bl || !vkUserId) return; client.get(`/dragon/${id}`, { params: { vk_id: vkUserId } }).then((r) => setD(r.data)).finally(() => setLoad(false)); }, [id, vkUserId, bl]);

  if (bl || load) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="dragon-skeleton-card" style={{ height: 300 }} /></div>;
  if (!d) return <div className="lair-card" style={{ maxWidth: 400, margin: '40px auto', textAlign: 'center' }}><div className="lair-empty-icon">🐉</div><p style={{ color: 'var(--text-secondary)' }}>Дракон не найден</p></div>;

   const pct = d.steps_count ? Math.round((d.user_progress.completed_steps / d.steps_count) * 100) : 0;
   const clr = d.family_color || 'var(--accent-gold-light)';
   const hasTimeout = !!d.next_step_available_at && d.user_progress.completed_steps > 0;
   const prevCompleted = hasTimeout ? Math.max(0, d.user_progress.completed_steps - 1) : d.user_progress.completed_steps;
   const prevPct = d.steps_count ? Math.round((prevCompleted / d.steps_count) * 100) : 0;
   const extraPct = pct - prevPct;

  return (
    <div style={{ padding: 20 }}>
      <button
        onClick={() => nav(-1)}
        className="lair-btn lair-btn-outline lair-btn-sm"
        style={{ marginBottom: 12, fontSize: 15, padding: '8px 18px' }}
      >
        ← Назад
      </button>
      <div className="lair-card lair-rise" style={{ textAlign: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 8 }}>
          {d.is_revealed
            ? (d.dragon_url
                ? <img src={`${mediaUrl(d.dragon_url)}?v=${d.rarity}`} alt="" onClick={() => setZoom(`${mediaUrl(d.dragon_url)}?v=${d.rarity}`)} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 'var(--radius-md)', cursor: 'pointer' }} />
                : <span style={{ fontSize: 64 }}>🐉</span>)
            : (d.egg_url
                ? <img src={mediaUrl(d.egg_url)} alt="" onClick={() => setZoom(mediaUrl(d.egg_url))} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 'var(--radius-md)', cursor: 'pointer' }} />
                : <span style={{ fontSize: 64 }}>🥚</span>)}
        </div>
        <h2 style={{ margin: '0 0 4px', color: clr, fontSize: 22 }}>
          {d.is_revealed ? d.name : `Яйцо: ${d.egg_type}`}
        </h2>
        {d.is_revealed && <div style={{ color: 'var(--text-secondary)', fontSize: 15, marginBottom: 12 }}>Редкость: <span style={{ color: 'var(--gold)' }}>{'★'.repeat(d.rarity || 1)}</span></div>}
        {d.is_revealed && d.description && <p style={{ color: 'var(--text-secondary)', fontSize: 16, fontStyle: 'italic' }}>{d.description}</p>}
      </div>

      {!d.is_revealed && d.user_progress.completed_steps > 0 && (
      <>
        <div className="lair-card" style={{ marginBottom: 16 }}>
          <div style={{ position: 'relative' }}>
            <div style={{ marginTop: 0, background: 'var(--bg-card-hover)', borderRadius: 'var(--radius-sm)', height: 10, overflow: 'hidden', display: 'flex' }}>
              <div style={{
                height: '100%',
                width: `${prevPct}%`,
                background: `linear-gradient(90deg, ${clr}88, ${clr})`,
                borderRadius: 'var(--radius-sm) 0 0 var(--radius-sm)',
                transition: 'width 0.5s',
                flexShrink: 0,
              }} />
              {hasTimeout && extraPct > 0 && (
                <div style={{
                  height: '100%',
                  width: `${extraPct}%`,
                  background: `linear-gradient(90deg, ${clr}88, ${clr})`,
                  opacity: 0.3,
                  transition: 'width 0.5s',
                  flexShrink: 0,
                }} />
              )}
            </div>
            {hasTimeout && extraPct > 0 && (
              <div style={{
                position: 'absolute',
                left: `${prevPct}%`,
                width: `${extraPct}%`,
                top: 0,
                bottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
              }}>
                <span className="hourglass-flip" style={{ fontSize: 8, lineHeight: 1, display: 'inline-block' }}>⏳</span>
              </div>
            )}
          </div>
          <div style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 4 }}>{prevPct}%</div>
        </div>

       <div className="lair-card">
         {d.user_progress.steps.filter((s) => d.next_step_available_at ? s.completed : s.number <= d.user_progress.completed_steps + 1).map((s) => {
           const isTimeoutStep = hasTimeout && s.completed && s.number === d.user_progress.completed_steps;
           return (
           <div key={s.number} style={{
             padding: '12px 16px', marginBottom: 8, borderRadius: 'var(--radius-sm)',
             background: isTimeoutStep ? 'rgba(201,138,42,0.2)' : s.completed ? 'var(--success-bg)' : s.number === d.user_progress.completed_steps + 1 ? 'var(--warning-bg)' : 'var(--bg-card)',
             border: '1px solid var(--border-color)',
           }}>
             <span style={{ marginRight: 8 }}>
                {isTimeoutStep
                  ? <span className="hourglass-flip" style={{ display: 'inline-block' }}>⏳</span>
                  : s.completed
                   ? '✅'
                   : s.number === d.user_progress.completed_steps + 1
                     ? '→'
                     : '📋'}
             </span>
              <span style={{ fontSize: 16, color: s.completed ? 'var(--text-secondary)' : 'var(--text-primary)' }}>
                {s.task}
              </span>
            </div>
         );
         })}
       </div>
      </>
      )}
      <style>{`.dragon-skeleton-card{height:300px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:sh 1.5s infinite}@keyframes sh{0%,100%{opacity:.4}50%{opacity:.7}}.hourglass-flip{animation:hg 3s ease-in-out infinite}@keyframes hg{0%{transform:rotateY(0)}45%{transform:rotateY(0)}55%{transform:rotateY(180deg)}100%{transform:rotateY(180deg)}}`}</style>
      {zoom && (
        <div onClick={() => setZoom(null)}
             style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          <img src={zoom} alt="" onClick={(e) => e.stopPropagation()}
               style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain', borderRadius: 8, boxShadow: '0 0 60px rgba(153,102,255,0.3)' }} />
          <button onClick={() => setZoom(null)}
                  style={{ position: 'absolute', top: 16, right: 16, background: 'none', border: 'none', color: '#fff', fontSize: 32, cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>
      )}
    </div>
  );
}

export default DragonDetail;
