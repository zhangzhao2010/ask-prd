'use client';

import '@cloudscape-design/global-styles/index.css';
import './globals.css';
import { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  AppLayout,
  TopNavigation,
  SideNavigation,
  SideNavigationProps,
  TopNavigationProps,
  Modal,
  Box,
  SpaceBetween,
  FormField,
  Input,
  Button,
  Alert,
} from '@cloudscape-design/components';
import { authService } from '@/services/auth';
import { apiClient } from '@/services/api';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [navigationOpen, setNavigationOpen] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);
  const [changePasswordModalVisible, setChangePasswordModalVisible] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);

  // 检查认证状态
  useEffect(() => {
    const checkAuth = () => {
      setIsAuthenticated(authService.isAuthenticated());
      setUsername(authService.getUsername() || '');
      setIsAdmin(authService.isAdmin());
    };

    checkAuth();

    // 监听storage变化（其他tab登录/登出）
    window.addEventListener('storage', checkAuth);
    return () => window.removeEventListener('storage', checkAuth);
  }, [pathname]);

  // 处理登出
  const handleLogout = () => {
    authService.logout();
    router.push('/login');
  };

  // 处理修改密码
  const handleChangePassword = async () => {
    setPasswordError('');
    setPasswordSuccess('');

    // 验证输入
    if (!oldPassword || !newPassword || !confirmPassword) {
      setPasswordError('请填写所有字段');
      return;
    }

    if (newPassword.length < 6) {
      setPasswordError('新密码至少需要6位');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('两次输入的新密码不一致');
      return;
    }

    setChangingPassword(true);
    try {
      await apiClient.changePassword(oldPassword, newPassword);
      setPasswordSuccess('密码修改成功');
      // 清空表单
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      // 3秒后关闭modal
      setTimeout(() => {
        setChangePasswordModalVisible(false);
        setPasswordSuccess('');
      }, 2000);
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : '密码修改失败');
    } finally {
      setChangingPassword(false);
    }
  };

  // 侧边导航配置
  const sideNavigationItems: SideNavigationProps.Item[] = [
    {
      type: 'link',
      text: '首页',
      href: '/',
    },
    { type: 'divider' },
    {
      type: 'section',
      text: '知识库管理',
      items: [
        {
          type: 'link',
          text: '知识库列表',
          href: '/knowledge-bases',
        },
        {
          type: 'link',
          text: '文档管理',
          href: '/documents',
        },
      ],
    },
    { type: 'divider' },
    {
      type: 'link',
      text: '智能问答',
      href: '/query',
    },
    // 管理员功能
    ...(isAdmin
      ? [
          { type: 'divider' as const },
          {
            type: 'section' as const,
            text: '系统管理',
            items: [
              {
                type: 'link' as const,
                text: '用户管理',
                href: '/admin/users',
              },
            ],
          },
        ]
      : []),
  ];

  // 顶部导航配置
  const utilities: TopNavigationProps.Utility[] = [
    {
      type: 'button',
      text: '文档',
      href: 'https://github.com/yourusername/ask-prd',
      external: true,
      externalIconAriaLabel: '打开新窗口',
    },
  ];

  // 如果已登录，添加用户菜单
  if (isAuthenticated) {
    utilities.push({
      type: 'menu-dropdown',
      text: username,
      description: isAdmin ? '管理员' : '用户',
      iconName: 'user-profile',
      items: [
        ...(isAdmin
          ? [
              {
                id: 'admin-users',
                text: '用户管理',
              },
            ]
          : []),
        { id: 'change-password', text: '修改密码' },
        { id: 'logout', text: '登出' },
      ],
      onItemClick: ({ detail }) => {
        if (detail.id === 'logout') {
          handleLogout();
        } else if (detail.id === 'admin-users') {
          router.push('/admin/users');
        } else if (detail.id === 'change-password') {
          setChangePasswordModalVisible(true);
        }
      },
    });
  } else if (pathname !== '/login') {
    // 未登录且不在登录页，显示登录按钮
    utilities.push({
      type: 'button',
      text: '登录',
      onClick: () => router.push('/login'),
    });
  }

  const topNavigation = (
    <TopNavigation
      identity={{
        href: '/',
        title: 'ASK-PRD',
        logo: {
          src: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHJ4PSI0IiBmaWxsPSIjMjMyRjNFIi8+CiAgPHBhdGggZD0iTTggMjRMMTYgOEwyNCAyNCIgc3Ryb2tlPSIjRkZGRkZGIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgogIDxwYXRoIGQ9Ik0xMiAxOEgyMCIgc3Ryb2tlPSIjRkZGRkZGIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K',
          alt: 'ASK-PRD',
        },
      }}
      utilities={utilities}
    />
  );

  // 侧边导航配置
  const sideNavigation = (
    <SideNavigation
      activeHref={pathname}
      items={sideNavigationItems}
      onFollow={(event) => {
        if (!event.detail.external) {
          event.preventDefault();
          router.push(event.detail.href);
        }
      }}
    />
  );

  // 登录页面和禁止访问页面不显示侧边导航
  const showSideNavigation = !['/login', '/forbidden'].includes(pathname);

  return (
    <html lang="zh-CN">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>ASK-PRD - 智能PRD检索问答系统</title>
        <meta name="description" content="基于PRD文档的智能检索问答系统" />
      </head>
      <body>
        <div id="app-root">
          {topNavigation}
          <AppLayout
            navigation={showSideNavigation ? sideNavigation : undefined}
            navigationOpen={showSideNavigation && navigationOpen}
            onNavigationChange={({ detail }) => setNavigationOpen(detail.open)}
            content={children}
            toolsHide
            headerSelector="#top-navigation"
          />

          {/* 修改密码Modal */}
          <Modal
            visible={changePasswordModalVisible}
            onDismiss={() => {
              setChangePasswordModalVisible(false);
              setOldPassword('');
              setNewPassword('');
              setConfirmPassword('');
              setPasswordError('');
              setPasswordSuccess('');
            }}
            header="修改密码"
            footer={
              <Box float="right">
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    variant="link"
                    onClick={() => {
                      setChangePasswordModalVisible(false);
                      setOldPassword('');
                      setNewPassword('');
                      setConfirmPassword('');
                      setPasswordError('');
                      setPasswordSuccess('');
                    }}
                  >
                    取消
                  </Button>
                  <Button
                    variant="primary"
                    onClick={handleChangePassword}
                    loading={changingPassword}
                  >
                    确认修改
                  </Button>
                </SpaceBetween>
              </Box>
            }
          >
            <SpaceBetween size="m">
              {passwordError && (
                <Alert type="error" dismissible onDismiss={() => setPasswordError('')}>
                  {passwordError}
                </Alert>
              )}

              {passwordSuccess && (
                <Alert type="success">
                  {passwordSuccess}
                </Alert>
              )}

              <FormField label="旧密码" description="请输入当前密码">
                <Input
                  value={oldPassword}
                  onChange={({ detail }) => setOldPassword(detail.value)}
                  placeholder="旧密码"
                  type="password"
                />
              </FormField>

              <FormField label="新密码" description="至少6位字符">
                <Input
                  value={newPassword}
                  onChange={({ detail }) => setNewPassword(detail.value)}
                  placeholder="新密码"
                  type="password"
                />
              </FormField>

              <FormField label="确认新密码" description="请再次输入新密码">
                <Input
                  value={confirmPassword}
                  onChange={({ detail }) => setConfirmPassword(detail.value)}
                  placeholder="确认新密码"
                  type="password"
                />
              </FormField>
            </SpaceBetween>
          </Modal>
        </div>
      </body>
    </html>
  );
}
