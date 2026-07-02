interface Props {
  status: 'locked' | 'growing' | 'completed';
  progressPct: number;
  name?: string;
  silhouetteUrl?: string;
  imageUrl?: string;
  onClick?: () => void;
  size?: number;
}

function DragonCell({ status, progressPct, name, imageUrl, onClick, size = 56 }: Props) {
  const bg =
    status === 'completed' ? '#e8f5e9' :
    status === 'growing' ? '#fff3e0' :
    '#f0f0f0';

  return (
    <div
      onClick={status !== 'locked' ? onClick : undefined}
      style={{
        width: size,
        height: size,
        borderRadius: 8,
        background: bg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: status !== 'locked' ? 'pointer' : 'default',
        fontSize: 12,
        fontWeight: status === 'completed' ? 'bold' : 'normal',
        border: status === 'growing' ? '2px solid #ff9800' : '1px solid #ddd',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {status === 'completed' && imageUrl && (
        <img src={imageUrl} alt={name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      )}
      {status === 'completed' && !imageUrl && <span>{name?.charAt(0) || '✓'}</span>}
      {status === 'growing' && <span style={{ fontSize: 11 }}>{progressPct}%</span>}
      {status === 'locked' && <span style={{ color: '#999' }}>?</span>}
    </div>
  );
}

export default DragonCell;
