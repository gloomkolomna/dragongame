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

function UserDragonProgress() {
  const { vkId, dragonId } = useParams<{ vkId: string; dragonId: string }>();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<StepInfo[]>([]);
  const [dragonName, setDragonName] = useState('');
  const [total, setTotal] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [load, setLoad] = useState(true);
  const [updating, setUpdating] = useState(false);

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
    } finally {
      setLoad(false);
    }
  };

  useEffect(() => { fetchData(); }, [vkId, dragonId]);

  const toggle = async (num: number) => {
    setUpdating(true);
    try {
      await client.post(`/admin/users/${vkId}/steps/${num}/toggle`, { dragon_id: Number(dragonId) });
      fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
    setUpdating(false);
  };

  const skipStep = async () => {
    if (!window.confirm('Пропустить текущий шаг?')) return;
    try {
      await client.post(`/admin/users/${vkId}/skip-step`, { dragon_id: Number(dragonId) });
      fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
  };

  const resetDragon = async () => {
    if (!window.confirm('Сбросить весь прогресс по этому дракону?')) return;
    try {
      await client.post(`/admin/users/${vkId}/reset-dragon`, { dragon_id: Number(dragonId) });
      fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
  };

  const restartDragon = async () => {
    if (!window.confirm('Возобновить выращивание заново?')) return;
    try {
      await client.post(`/admin/users/${vkId}/dragons/${dragonId}/restart`);
      fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
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
            <button className="lair-btn lair-btn-outline" onClick={resetDragon} disabled={updating}
                    style={{ color: 'var(--fire)', borderColor: 'var(--fire)' }}>
              ♻ Сбросить прогресс
            </button>
            <button className="lair-btn lair-btn-outline" onClick={restartDragon} disabled={updating}>
              🔄 Начать заново
            </button>
          </div>
        </>
      )}

      <style>{`.lair-skeleton{height:300px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:sh 1.5s infinite}@keyframes sh{0%,100%{opacity:.4}50%{opacity:.7}}`}</style>
    </div>
  );
}

export default UserDragonProgress;
