import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useVkBridge } from '../context/VkBridgeContext';
import client from '../api/client';
import { mediaUrl } from '../api/media';

interface Step { number: number; task: string; completed: boolean; }
interface Dragon { is_revealed: boolean; name?: string; rarity?: number; egg_type: string; steps_count: number; description?: string; dragon_url?: string; egg_url?: string; user_progress: { status: string; completed_steps: number; steps: Step[] }; }

function DragonDetail() {
  const { id } = useParams<{ id: string }>();
  const { vkUserId, loading: bl } = useVkBridge();
  const [d, setD] = useState<Dragon | null>(null);
  const [load, setLoad] = useState(true);
  const nav = useNavigate();

  useEffect(() => { if (bl || !vkUserId) return; client.get(`/dragon/${id}`, { params: { vk_id: vkUserId } }).then((r) => setD(r.data)).finally(() => setLoad(false)); }, [id, vkUserId, bl]);

  if (bl || load) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="dragon-skeleton-card" style={{ height: 300 }} /></div>;
  if (!d) return <div className="lair-card" style={{ maxWidth: 400, margin: '40px auto', textAlign: 'center' }}><div className="lair-empty-icon">🐉</div><p style={{ color: 'var(--text-secondary)' }}>Дракон не найден</p></div>;

  const pct = d.steps_count ? Math.round((d.user_progress.completed_steps / d.steps_count) * 100) : 0;

  return (
    <div style={{ maxWidth: 500, margin: '0 auto', padding: 20 }}>
      <button
        onClick={() => nav(-1)}
        className="lair-btn lair-btn-outline lair-btn-sm"
        style={{ marginBottom: 12 }}
      >
        ← Назад
      </button>
      <div className="lair-card lair-rise" style={{ textAlign: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 8 }}>
          {d.is_revealed
            ? (d.dragon_url
                ? <img src={`${mediaUrl(d.dragon_url)}?v=${d.rarity}`} alt="" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 240, borderRadius: 'var(--radius-md)' }} />
                : <span style={{ fontSize: 56 }}>🐉</span>)
            : (d.egg_url
                ? <img src={mediaUrl(d.egg_url)} alt="" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 240, borderRadius: 'var(--radius-md)' }} />
                : <span style={{ fontSize: 56 }}>🥚</span>)}
        </div>
        <h2 style={{ margin: '0 0 4px', color: 'var(--accent-gold-light)', fontSize: 18 }}>
          {d.is_revealed ? d.name : `Яйцо: ${d.egg_type}`}
        </h2>
        {d.is_revealed && <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 12 }}>Редкость: {'⭐'.repeat(d.rarity || 1)}</div>}
        {d.is_revealed && d.description && <p style={{ color: 'var(--text-secondary)', fontSize: 14, fontStyle: 'italic' }}>{d.description}</p>}

        <div style={{ marginTop: 12, background: 'var(--bg-card-hover)', borderRadius: 'var(--radius-sm)', height: 8, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg, var(--accent-gold-dark), var(--accent-gold-light))', borderRadius: 'var(--radius-sm)', transition: 'width 0.5s' }} />
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{pct}%</div>
      </div>

      <div className="lair-card">
        {d.user_progress.steps.map((s) => (
          <div key={s.number} style={{
            padding: '10px 14px', marginBottom: 6, borderRadius: 'var(--radius-sm)',
            background: s.completed ? 'var(--success-bg)' : s.number === d.user_progress.completed_steps + 1 ? 'var(--warning-bg)' : 'var(--bg-card)',
            border: '1px solid var(--border-color)',
          }}>
            <span style={{ marginRight: 8 }}>{s.completed ? '✅' : s.number === d.user_progress.completed_steps + 1 ? '→' : '📋'}</span>
            <span style={{ fontSize: 14, color: s.completed ? 'var(--text-secondary)' : 'var(--text-primary)' }}>
              {s.task}
            </span>
          </div>
        ))}
      </div>
      <style>{`.dragon-skeleton-card{height:300px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:sh 1.5s infinite}@keyframes sh{0%,100%{opacity:.4}50%{opacity:.7}}`}</style>
    </div>
  );
}

export default DragonDetail;
