'use client';

import '@cloudscape-design/global-styles/index.css';
import './globals.css';
import { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  AppLayout,
  TopNavigation,
  SideNavigation,
  SideNavigationProps,
} from '@cloudscape-design/components';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [navigationOpen, setNavigationOpen] = useState(true);

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
  ];

  // 顶部导航配置
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
      utilities={[
        {
          type: 'button',
          text: '文档',
          href: 'https://github.com/yourusername/ask-prd',
          external: true,
          externalIconAriaLabel: '打开新窗口',
        },
        {
          type: 'menu-dropdown',
          text: '设置',
          items: [
            { id: 'api-config', text: 'API配置' },
            { id: 'about', text: '关于' },
          ],
        },
      ]}
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
            navigation={sideNavigation}
            navigationOpen={navigationOpen}
            onNavigationChange={({ detail }) => setNavigationOpen(detail.open)}
            content={children}
            toolsHide
            headerSelector="#top-navigation"
          />
        </div>
      </body>
    </html>
  );
}
