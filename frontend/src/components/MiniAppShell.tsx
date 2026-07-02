import { type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

function MiniAppShell({ children }: Props) {
  return <>{children}</>;
}

export default MiniAppShell;
