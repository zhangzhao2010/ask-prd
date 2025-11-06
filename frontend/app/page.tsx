'use client';

import { useRouter } from 'next/navigation';
import {
  Container,
  Header,
  SpaceBetween,
  Button,
  Box,
  ColumnLayout,
  Cards,
} from '@cloudscape-design/components';

export default function Home() {
  const router = useRouter();

  // 功能卡片数据
  const featureCards = [
    {
      id: 'knowledge-base',
      title: '知识库管理',
      description: '创建和管理PRD文档知识库，支持多个知识库隔离管理',
      icon: '📚',
      action: () => router.push('/knowledge-bases'),
      actionText: '管理知识库',
    },
    {
      id: 'documents',
      title: '文档上传',
      description: '上传PDF格式的PRD文档，自动转换为Markdown并提取图片',
      icon: '📄',
      action: () => router.push('/documents'),
      actionText: '管理文档',
    },
    {
      id: 'query',
      title: '智能问答',
      description: '基于Multi-Agent架构的智能问答，支持图文混排文档的深度理解',
      icon: '💬',
      action: () => router.push('/query'),
      actionText: '开始提问',
    },
  ];

  return (
    <SpaceBetween size="l">
      {/* 欢迎区域 */}
      <Container
        header={
          <Header
            variant="h1"
            description="基于PRD文档的智能检索问答系统 - Multi-Agent Demo"
          >
            欢迎使用 ASK-PRD
          </Header>
        }
      >
        <SpaceBetween size="m">
          <Box variant="p">
            ASK-PRD 是一个智能文档检索问答系统，专为PRD（产品需求文档）场景设计。
            系统采用Multi-Agent架构，能够深度理解图文混排文档，回答跨文档的复杂问题。
          </Box>

          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">核心技术</Box>
              <Box variant="p">
                AWS Bedrock + Claude Sonnet 4.5<br />
                Multi-Agent协作架构<br />
                OpenSearch向量检索
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">主要特性</Box>
              <Box variant="p">
                图文混排文档理解<br />
                跨文档问题推理<br />
                实时流式输出
              </Box>
            </div>
            <div>
              <Box variant="awsui-key-label">文档支持</Box>
              <Box variant="p">
                PDF自动转换<br />
                图片内容理解<br />
                精准引用定位
              </Box>
            </div>
          </ColumnLayout>

          <Box textAlign="center">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="primary" onClick={() => router.push('/query')}>
                开始使用
              </Button>
              <Button onClick={() => router.push('/knowledge-bases')}>
                管理知识库
              </Button>
            </SpaceBetween>
          </Box>
        </SpaceBetween>
      </Container>

      {/* 功能卡片 */}
      <Cards
        cardDefinition={{
          header: (item) => (
            <Box fontSize="heading-l" padding={{ top: 's' }}>
              {item.icon} {item.title}
            </Box>
          ),
          sections: [
            {
              id: 'description',
              content: (item) => item.description,
            },
            {
              id: 'action',
              content: (item) => (
                <Button onClick={item.action}>{item.actionText}</Button>
              ),
            },
          ],
        }}
        items={featureCards}
        cardsPerRow={[{ cards: 1 }, { minWidth: 500, cards: 3 }]}
        header={
          <Header variant="h2">快速开始</Header>
        }
      />

      {/* 使用流程 */}
      <Container
        header={
          <Header variant="h2">
            使用流程
          </Header>
        }
      >
        <ColumnLayout columns={3} variant="text-grid">
          <div>
            <Box variant="h3">1. 创建知识库</Box>
            <Box variant="p">
              配置S3存储路径和OpenSearch索引，创建独立的知识库实例
            </Box>
          </div>
          <div>
            <Box variant="h3">2. 上传文档</Box>
            <Box variant="p">
              上传PDF格式的PRD文档，系统自动转换并提取图片内容
            </Box>
          </div>
          <div>
            <Box variant="h3">3. 智能问答</Box>
            <Box variant="p">
              提出问题，Multi-Agent协作深度理解文档并生成答案
            </Box>
          </div>
        </ColumnLayout>
      </Container>

      {/* 系统信息 */}
      <Container
        header={
          <Header variant="h2">
            系统架构
          </Header>
        }
      >
        <SpaceBetween size="s">
          <Box variant="p">
            <strong>KnowledgeBase Builder</strong>: 使用marker转换PDF为Markdown，
            通过Claude Vision API理解图片内容，使用Titan Embeddings向量化后存入OpenSearch
          </Box>
          <Box variant="p">
            <strong>Agentic Robot</strong>: Query Rewrite重写查询，
            Hybrid Search混合检索（kNN + BM25），
            Multi-Agent协作（Sub-Agent深度阅读 + Main-Agent综合答案）
          </Box>
          <Box variant="p">
            <strong>前端技术栈</strong>: Next.js 15 + AWS Cloudscape Design System + TypeScript
          </Box>
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
}
