import { type ReactNode, Suspense, lazy } from 'react';
import { useVkBridge } from '../context/VkBridgeContext';

interface Props {
  children: ReactNode;
}

const VkuiWrapper = lazy(() => import('./VkuiWrapper'));

function MiniAppShell({ children }: Props) {
  const { isVkWebView } = useVkBridge();

  if (!isVkWebView) {
    return <>{children}</>;
  }

  return (
    <Suspense fallback={<>{children}</>}>
      <VkuiWrapper>{children}</VkuiWrapper>
    </Suspense>
  );
}

export default MiniAppShell;
