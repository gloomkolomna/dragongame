import { type ReactNode } from 'react';
import { AdaptivityProvider, AppRoot } from '@vkontakte/vkui';
import '@vkontakte/vkui/dist/vkui.css';

interface Props {
  children: ReactNode;
}

function VkuiWrapper({ children }: Props) {
  return (
    <AdaptivityProvider>
      <AppRoot mode="embedded" scroll="contain">
        {children}
      </AppRoot>
    </AdaptivityProvider>
  );
}

export default VkuiWrapper;
