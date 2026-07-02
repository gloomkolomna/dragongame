import { Button } from '@vkontakte/vkui';

interface Props {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmDialog({ message, onConfirm, onCancel }: Props) {
  return (
    <div style={{ padding: 16, textAlign: 'center' }}>
      <p>{message}</p>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
        <Button mode="secondary" onClick={onCancel}>Отмена</Button>
        <Button mode="primary" onClick={onConfirm}>Подтвердить</Button>
      </div>
    </div>
  );
}

export default ConfirmDialog;
