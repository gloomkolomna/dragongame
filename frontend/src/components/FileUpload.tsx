interface Props {
  onUpload: (file: File) => void;
  accept?: string;
  label?: string;
}

function FileUpload({ onUpload, accept = 'image/*', label = 'Загрузить изображение' }: Props) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  return (
    <div style={{ margin: '8px 0' }}>
      <label style={{ display: 'block', marginBottom: 4, color: '#666' }}>{label}</label>
      <input type="file" accept={accept} onChange={handleChange} />
    </div>
  );
}

export default FileUpload;
