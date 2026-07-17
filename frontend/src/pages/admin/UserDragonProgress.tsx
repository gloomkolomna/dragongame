import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface StepInfo {
  step_number: number;
  task_description: string;
  magic_action: string;
  hint: string;
  completed: boolean;
  current: boolean;
}

interface CareStage { id: number; stage_number: number; name: string; cycles_count: number; }
interface CareAction { order_in_cycle: number; action_label: string; action_type: string; }
interface CareState {
  has_care: boolean;
  dragon_id: number;
  stage_id: number;
  stage_name: string;
  stage_number: number;
  cycles_completed: number;
  cycles_total: number;
  current_action_order: number;
  current_action_label: string;
  current_sub_action_id: number | null;
  current_sub_action_label: string;
  current_step_order: number;
  stages: CareStage[];
  actions: CareAction[];
}

function UserDragonProgress() {
  const { vkId, dragonId } = useParams<{ vkId: string; dragonId: string }>();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<StepInfo[]>([]);
  const [dragonName, setDragonName] = useState('');
  const [total, setTotal] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [load, setLoad] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [care, setCare] = useState<CareState | null>(null);

  const fetchData = async () => {
    if (!vkId || !dragonId) return;
    try {
      const r = await client.get(`/admin/users/${vkId}/dragons/${dragonId}/steps`);
      setSteps(r.data.steps);
      setDragonName(r.data.dragon_name);
      setTotal(r.data.total);
      setCurrentStep(r.data.current_step);
    } catch (e) {
      console.error(e);
    }
    try {
      const c = await client.get(`/admin/users/${vkId}/epic-care`);
      setCare(c.data.has_care ? c.data : null);
    } catch {
      setCare(null);
    } finally {
      setLoad(false);
    }
  };

  useEffect(() => { fetchData(); }, [vkId, dragonId]);

  const toggle = async (num: number) => {
    if (!window.confirm('Переключить статус шага (завершён / не завершён)?')) return;
    setUpdating(true);
    try {
      await client.post(`/admin/users/${vkId}/steps/${num}/toggle`, { dragon_id: Number(dragonId) });
      await fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
    setUpdating(false);
  };

  const skipStep = async () => {
    if (!window.confirm('Пропустить текущий шаг?')) return;
    setUpdating(true);
    try {
      await client.post(`/admin/users/${vkId}/skip-step`, { dragon_id: Number(dragonId) });
      await fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
    setUpdating(false);
  };

  const restartDragon = async () => {
    if (!window.confirm('Начать выращивание заново с 1-го шага?')) return;
    setUpdating(true);
    try {
      await client.post(`/admin/users/${vkId}/dragons/${dragonId}/restart`);
      await fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
    setUpdating(false);
  };

  const careAction = async (path: string, body?: any, confirmMsg?: string) => {
    if (confirmMsg && !window.confirm(confirmMsg)) return;
    setUpdating(true);
    try {
      await client.post(`/admin/users/${vkId}/epic-care/${path}`, body || {});
      await fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
    setUpdating(false);
  };

  const careGoto = async (patch: Partial<{ stage_id: number; action_order: number; cycles_completed: number }>) => {
    await careAction('goto', patch);
  };

  const completed = steps.filter((s) => s.completed).length;
  const pct = total ? Math.round((completed / total) * 100) : 0;
  return (
    <div style={{ padding: 20 }}>
      <button onClick={() => navigate(`/admin/users?vk_id=${vkId}`)} className="lair-btn lair-btn-outline lair-btn-sm"
              style={{ marginBottom: 12, fontSize: 15, padding: '8px 18px' }}>
        ← Назад
      </button>

      {load ? (
        <div className="lair-skeleton" />
      ) : (
        <>
          <div className="lair-card" style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 20, color: 'var(--accent-gold-light)', fontWeight: 600, marginBottom: 4 }}>
              🥚 {dragonName || `Дракон #${dragonId}`}
            </div>
            <div style={{ fontSize: 14, color: 'var(--parchment-dim)' }}>
              Шаг: {currentStep || '—'} из {total} &nbsp;|&nbsp; Выполнено: {completed} &nbsp;|&nbsp; {pct}%
            </div>
            <div style={{ marginTop: 8, background: 'var(--bg-card-hover)', borderRadius: 6, height: 8, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg, var(--accent-gold-dark), var(--accent-gold-light))', borderRadius: 6, transition: 'width 0.3s' }} />
            </div>
          </div>

          <div className="lair-card" style={{ marginBottom: 16, padding: 0, overflow: 'hidden' }}>
            <table className="lair-table">
              <thead>
                <tr>
                  <th style={{ width: 50 }}>#</th>
                  <th>Задание</th>
                  <th style={{ width: 100 }}>Статус</th>
                  <th style={{ width: 100 }}></th>
                </tr>
              </thead>
              <tbody>
                {steps.map((s) => (
                  <tr key={s.step_number} style={{ background: s.current ? 'var(--warning-bg)' : undefined }}>
                    <td>{s.step_number}</td>
                    <td>
                      {s.magic_action && <div style={{ fontWeight: 600, marginBottom: 2 }}>{s.magic_action}</div>}
                      <div style={{ fontSize: 13, color: 'var(--parchment-dim)' }}>{s.task_description}</div>
                      {s.hint && <div style={{ fontSize: 12, color: 'var(--parchment-faded)' }}>💡 {s.hint}</div>}
                    </td>
                    <td>
                      {s.completed ? (
                        <span style={{ color: 'var(--success)', fontSize: 13 }}>✅ Выполнено</span>
                      ) : s.current ? (
                        <span style={{ color: 'var(--accent-gold)', fontSize: 13 }}>→ Текущий</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>📋 Ожидает</span>
                      )}
                    </td>
                    <td>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" style={{ fontSize: 11 }}
                              onClick={() => toggle(s.step_number)}>
                        {s.completed ? '↩ Отменить' : '✅ Завершить'}
                      </button>
                    </td>
                  </tr>
                ))}
                {steps.length === 0 && (
                  <tr><td colSpan={4} style={{ textAlign: 'center', padding: 24, color: 'var(--parchment-faded)' }}>Шаги не найдены</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="lair-btn lair-btn-outline" onClick={skipStep} disabled={updating}>
              ⏩ Пропустить шаг
            </button>
            <button className="lair-btn lair-btn-outline" onClick={restartDragon} disabled={updating}>
              🔄 Начать заново
            </button>
          </div>

          {care && care.dragon_id === Number(dragonId) && (
            <div className="lair-card" style={{ marginTop: 16 }}>
              <h4 style={{ color: 'var(--gold)', margin: '0 0 12px' }}>🐲 Уход за эпическим драконом</h4>
              <div style={{ fontSize: 14, color: 'var(--parchment-dim)', marginBottom: 12 }}>
                Стадия <strong style={{ color: 'var(--accent-gold-light)' }}>{care.stage_number}. {care.stage_name}</strong>
                <br />
                Действие: <strong>{care.current_action_label || '—'}</strong>
                {care.current_sub_action_id && <span style={{ color: 'var(--gold)' }}> · вариант «{care.current_sub_action_label}» (шаг {(care.current_step_order || 0) + 1})</span>}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 8, alignItems: 'center', maxWidth: 520, marginBottom: 12 }}>
                <label className="lair-label" style={{ margin: 0 }}>Стадия</label>
                <select className="lair-input" value={care.stage_id || ''} disabled={updating}
                        onChange={(e) => careGoto({ stage_id: Number(e.target.value), action_order: 0, cycles_completed: 0 })}>
                  {care.stages.map((s) => <option key={s.id} value={s.id}>{s.stage_number}. {s.name}</option>)}
                </select>

                <label className="lair-label" style={{ margin: 0 }}>Действие</label>
                <select className="lair-input" value={care.current_action_order || 0} disabled={updating || care.actions.length === 0}
                        onChange={(e) => careGoto({ action_order: Number(e.target.value) })}>
                  {care.actions.length === 0 && <option value={0}>— нет действий —</option>}
                  {care.actions.map((a, i) => <option key={i} value={i}>#{a.order_in_cycle} {a.action_label}{a.action_type === 'composite' ? ' (составное)' : ''}</option>)}
                </select>

                <label className="lair-label" style={{ margin: 0 }}>Циклов пройдено</label>
                <input className="lair-input" type="text" inputMode="numeric" value={care.cycles_completed || 0} disabled={updating}
                       onChange={(e) => setCare({ ...care, cycles_completed: parseInt(e.target.value, 10) || 0 })}
                       onBlur={(e) => careGoto({ cycles_completed: parseInt(e.target.value, 10) || 0 })}
                       style={{ maxWidth: 100 }} />
              </div>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button className="lair-btn" disabled={updating}
                        onClick={() => careAction('advance', {}, 'Завершить текущее действие и перейти к следующему?')}>
                  ✅ Завершить действие
                </button>
                {care.current_sub_action_id && (
                  <button className="lair-btn lair-btn-outline" disabled={updating}
                          onClick={() => careAction('clear-sub', {}, 'Сбросить выбор варианта?')}>
                    ↩ Сбросить выбор варианта
                  </button>
                )}
                <button className="lair-btn lair-btn-outline" disabled={updating}
                        onClick={() => careAction('restart', {}, 'Сбросить уход на первую стадию?')}>
                  🔄 Уход заново
                </button>
              </div>
            </div>
          )}
        </>
      )}

      <style>{`.lair-skeleton{height:300px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:sh 1.5s infinite}@keyframes sh{0%,100%{opacity:.4}50%{opacity:.7}}`}</style>
    </div>
  );
}

export default UserDragonProgress;
