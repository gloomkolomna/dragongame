import { useEffect, useState } from 'react';
import client from '../../api/client';

function SettingsPage() {
  const [keyword, setKeyword] = useState('');
  const [suspiciousMult, setSuspiciousMult] = useState(2);
  const [blockMult, setBlockMult] = useState(3);
  const [load, setLoad] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    client.get('/admin/settings')
      .then((r) => {
        setKeyword(r.data.welcome_keyword || '');
        setSuspiciousMult(r.data.suspicious_multiplier ?? 2);
        setBlockMult(r.data.block_multiplier ?? 3);
      })
      .finally(() => setLoad(false));
  }, []);

  const save = async () => {
    setSaving(true); setError(''); setSaved(false);
    try {
      const r = await client.put('/admin/settings', {
        welcome_keyword: keyword,
        suspicious_multiplier: suspiciousMult,
        block_multiplier: blockMult,
      });
      setKeyword(r.data.welcome_keyword);
      setSuspiciousMult(r.data.suspicious_multiplier);
      setBlockMult(r.data.block_multiplier);
      setSaved(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка');
    } finally {
      setSaving(false);
    }
  };

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header"><h2>⚙ Настройки</h2></div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        {saved && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(120,200,120,0.12)', color: 'var(--success)', fontSize: 13 }}>Сохранено</div>}

        <div className="lair-card" style={{ maxWidth: 420, marginBottom: 16 }}>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Ключевое слово для входа</label>
            <input
              className="lair-input"
              type="text"
              value={keyword}
              onChange={(e) => { setSaved(false); setKeyword(e.target.value); }}
              placeholder="дождались"
              style={{ width: '100%', fontSize: 18 }}
            />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              Бот будет отвечать новым игрокам только после этого слова. Если поле пустое — гейт отключён.
            </div>
          </div>
        </div>

        <div className="lair-card" style={{ maxWidth: 420, marginBottom: 16 }}>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Множитель подозрительного отчёта</label>
            <input
              className="lair-input"
              type="text"
              inputMode="numeric"
              value={suspiciousMult}
              onChange={(e) => { setSaved(false); setSuspiciousMult(Math.max(1, Number(e.target.value.replace(/\D/g, '')) || 1)); }}
              style={{ width: 100, fontSize: 18, fontFamily: 'var(--font-mono)' }}
            />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              Если заявлено стежков больше нормы × N — отчёт помечается подозрительным, шаг засчитывается. По умолчанию 2.
            </div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Множитель блокировки</label>
            <input
              className="lair-input"
              type="text"
              inputMode="numeric"
              value={blockMult}
              onChange={(e) => { setSaved(false); setBlockMult(Math.max(1, Number(e.target.value.replace(/\D/g, '')) || 1)); }}
              style={{ width: 100, fontSize: 18, fontFamily: 'var(--font-mono)' }}
            />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              Если заявлено стежков больше нормы × N — шаг блокируется и не засчитывается. По умолчанию 3.
            </div>
          </div>
        </div>

        <button className="lair-btn" disabled={saving} onClick={save}>{saving ? '...' : 'Сохранить'}</button>
      </div>
    </>
  );
}

export default SettingsPage;
