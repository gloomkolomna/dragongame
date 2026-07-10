import { useEffect, useRef, useState } from 'react';
import client from '../../api/client';

interface IntroChapter {
  id: number;
  chapter_number: number;
  text: string;
  image_path: string;
  is_active: boolean;
}

const EMPTY = { chapter_number: 1, text: '', is_active: true };

function IntroChaptersList() {
  const [chapters, setChapters] = useState<IntroChapter[]>([]);
  const [load, setLoad] = useState(true);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ ...EMPTY });
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const reload = () => {
    setLoad(true);
    client.get('/admin/intro-chapters')
      .then((r) => setChapters(r.data))
      .finally(() => setLoad(false));
  };

  useEffect(() => { reload(); }, []);

  const startNew = () => {
    setEditId(null);
    const maxNum = chapters.reduce((m, c) => Math.max(m, c.chapter_number), 0);
    setForm({ ...EMPTY, chapter_number: maxNum + 1 });
    setImageFile(null);
    setImagePreview('');
    setError('');
  };

  const startEdit = (ch: IntroChapter) => {
    setEditId(ch.id);
    setForm({ chapter_number: ch.chapter_number, text: ch.text, is_active: ch.is_active });
    setImageFile(null);
    setImagePreview(ch.image_path ? `/dragons/api/static/images/${ch.image_path}?t=${Date.now()}` : '');
    setError('');
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) { setImageFile(file); setImagePreview(URL.createObjectURL(file)); }
  };

  const save = async () => {
    if (form.chapter_number < 1) { setError('Номер главы должен быть ≥ 1'); return; }
    setSaving(true);
    setError('');
    try {
      const fd = new FormData();
      fd.append('chapter_number', String(form.chapter_number));
      fd.append('text', form.text);
      fd.append('is_active', String(form.is_active));
      if (imageFile) fd.append('image', imageFile);

      if (editId) {
        await client.put(`/admin/intro-chapters/${editId}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      } else {
        await client.post('/admin/intro-chapters', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      }
      startNew();
      await reload();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка');
    } finally {
      setSaving(false);
    }
  };

  const del = async (id: number) => {
    if (!window.confirm('Удалить главу?')) return;
    await client.delete(`/admin/intro-chapters/${id}`);
    await reload();
  };

  const imgUrl = (path: string) => `/dragons/api/static/images/${path}?t=${Date.now()}`;

  return (
    <>
      <div className="lair-header">
        <h2>📖 Вступительная история</h2>
      </div>
      <div className="lair-content">
        {error && (
          <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>
            {error}
          </div>
        )}

        <div className="lair-card" style={{ maxWidth: 720, marginBottom: 20 }}>
          <div style={{ fontWeight: 700, color: 'var(--gold)', marginBottom: 14 }}>
            {editId ? `Редактировать главу #${editId}` : 'Новая глава'}
          </div>

          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 14 }}>
            <div>
              <label className="lair-label">Номер главы</label>
              <input
                className="lair-input"
                type="number"
                min={1}
                value={form.chapter_number}
                onChange={(e) => setForm({ ...form, chapter_number: Number(e.target.value) || 1 })}
                style={{ width: 130 }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 4 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                />
                <span className="lair-label" style={{ margin: 0 }}>Активна</span>
              </label>
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            <label className="lair-label">Текст истории</label>
            <textarea
              className="lair-textarea"
              rows={6}
              value={form.text}
              onChange={(e) => setForm({ ...form, text: e.target.value })}
              placeholder="Текст главы..."
            />
          </div>

          <div style={{ marginBottom: 14 }}>
            <label className="lair-label">Картинка</label>
            <div onClick={() => fileRef.current?.click()} style={{
              width: 100, height: 100, borderRadius: 12,
              border: '2px dashed var(--bronze)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', overflow: 'hidden',
              background: 'var(--bg-input)',
              marginBottom: 4,
            }}>
              {imagePreview ? (
                <img src={imagePreview} alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                     onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
              ) : (
                <span style={{ fontSize: 28, opacity: 0.4 }}>+</span>
              )}
            </div>
            <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }}
                   onChange={handleImageChange} />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              {imageFile ? imageFile.name : 'PNG / JPG (не обязательно)'}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={save}>
              {saving ? '...' : editId ? 'Сохранить' : 'Добавить'}
            </button>
            {editId && (
              <button className="lair-btn lair-btn-outline" onClick={startNew}>Отмена</button>
            )}
          </div>
        </div>

        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          {load ? (
            <div className="lair-skeleton" />
          ) : (
            <table className="lair-table">
              <thead>
                <tr>
                  <th style={{ width: 60 }}>#</th>
                  <th style={{ width: 80 }}>Картинка</th>
                  <th>Текст</th>
                  <th style={{ width: 80 }}>Акт.</th>
                  <th style={{ width: 100 }}></th>
                </tr>
              </thead>
              <tbody>
                {chapters.map((ch) => (
                  <tr key={ch.id} className="clickable" onClick={() => startEdit(ch)} style={{ opacity: ch.is_active ? 1 : 0.5 }}>
                    <td style={{ fontWeight: 600 }}>Глава {ch.chapter_number}</td>
                    <td>
                      {ch.image_path ? (
                        <img src={imgUrl(ch.image_path)} alt="" style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--bronze)' }} />
                      ) : (
                        <span style={{ color: 'var(--parchment-faded)', fontSize: 13 }}>—</span>
                      )}
                    </td>
                    <td style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--parchment-dim)' }}>
                      {ch.text || '—'}
                    </td>
                    <td>{ch.is_active ? '✅' : '❌'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={(e) => { e.stopPropagation(); startEdit(ch); }}>✎</button>
                        <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={(e) => { e.stopPropagation(); del(ch.id); }}>✕</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {chapters.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16 }}>
                      Глав пока нет. Добавьте первую главу выше.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

export default IntroChaptersList;
