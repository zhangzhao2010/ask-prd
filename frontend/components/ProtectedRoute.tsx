'use client';

import { useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/services/auth';
import { Box, Spinner } from '@cloudscape-design/components';

interface ProtectedRouteProps {
  children: ReactNode;
  requireAdmin?: boolean; // 是否需要管理员权限
}

export function ProtectedRoute({
  children,
  requireAdmin = false,
}: ProtectedRouteProps) {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    // 检查认证状态
    const checkAuth = () => {
      // 1. 检查是否登录
      if (!authService.isAuthenticated()) {
        router.push('/login');
        return;
      }

      // 2. 如果需要管理员权限，检查角色
      if (requireAdmin && !authService.isAdmin()) {
        router.push('/forbidden');
        return;
      }

      // 通过验证
      setIsAuthorized(true);
      setIsChecking(false);
    };

    checkAuth();
  }, [router, requireAdmin]);

  // 显示加载状态
  if (isChecking) {
    return (
      <Box textAlign="center" padding={{ vertical: 'xxxl' }}>
        <Spinner size="large" />
        <Box variant="p" padding={{ top: 'm' }}>
          正在验证权限...
        </Box>
      </Box>
    );
  }

  // 已授权，显示内容
  if (isAuthorized) {
    return <>{children}</>;
  }

  // 未授权（实际上已经重定向，这里不会执行）
  return null;
}
