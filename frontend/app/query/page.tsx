'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Container,
  Header,
  SpaceBetween,
  Input,
  Button,
  Box,
  Select,
  FormField,
  Alert,
  Spinner,
  ColumnLayout,
} from '@cloudscape-design/components';
import ReactMarkdown from 'react-markdown';
import { knowledgeBaseAPI, queryAPI } from '@/services/api';
import type { KnowledgeBase, CitationItem, QueryStreamEvent } from '@/types';

function QueryPageContent() {
  const searchParams = useSearchParams();
  const [kbId, setKbId] = useState<string>(searchParams.get('kb_id') || '');
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [query, setQuery] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [answer, setAnswer] = useState('');
  const [citations, setCitations] = useState<CitationItem[]>([]);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [metrics, setMetrics] = useState<Record<string, number>>({});
  const answerRef = useRef<HTMLDivElement>(null);

  // 加载知识库列表
  const loadKnowledgeBases = async () => {
    try {
      const response = await knowledgeBaseAPI.list({ page: 1, page_size: 100 });
      setKnowledgeBases(response.items);
    } catch (error) {
      console.error('Failed to load knowledge bases:', error);
    }
  };

  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  // 处理SSE流式输出
  const handleQuery = async () => {
    if (!query.trim() || !kbId) return;

    // 重置状态
    setIsQuerying(true);
    setAnswer('');
    setCitations([]);
    setStatus('正在处理...');
    setError('');
    setMetrics({});

    try {
      const stream = await queryAPI.stream(kbId, query.trim());
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // 解码数据
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        // 保留最后一行（可能不完整）
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;

          // 解析SSE格式
          if (line.startsWith('event:')) {
            const eventType = line.substring(6).trim();
            // 下一行应该是data
            continue;
          } else if (line.startsWith('data:')) {
            const dataStr = line.substring(5).trim();
            try {
              const data = JSON.parse(dataStr) as QueryStreamEvent;

              // 处理不同类型的事件
              if (data.type === 'status') {
                setStatus((data as any).message);
              } else if (data.type === 'chunk') {
                // 正确的事件类型是 chunk，字段名是 content
                setAnswer((prev) => prev + (data as any).content);
                // 自动滚动到底部
                setTimeout(() => {
                  answerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
                }, 0);
              } else if (data.type === 'citation') {
                // 处理引用事件
                setCitations((prev) => [...prev, data as any]);
              } else if (data.type === 'tokens') {
                // Token统计事件
                const tokenData = data as any;
                setMetrics({
                  prompt_tokens: tokenData.prompt_tokens || 0,
                  completion_tokens: tokenData.completion_tokens || 0,
                  total_tokens: tokenData.total_tokens || 0,
                });
              } else if (data.type === 'done') {
                // 完成事件
                setStatus('完成');
                setIsQuerying(false);
              } else if (data.type === 'error') {
                const errorData = data as any;
                setError(errorData.message);
                setStatus('错误');
                setIsQuerying(false);
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e, dataStr);
            }
          }
        }
      }
    } catch (error: any) {
      setError(error.message || '查询失败');
      setStatus('错误');
      setIsQuerying(false);
    }
  };

  // 格式化Token数
  const formatTokens = (tokens?: number) => {
    if (!tokens) return '0';
    return tokens.toLocaleString();
  };

  // 格式化响应时间
  const formatTime = (ms?: number) => {
    if (!ms) return '0ms';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <SpaceBetween size="l">
      {/* 查询输入区 */}
      <Container
        header={
          <Header
            variant="h1"
            description="基于Multi-Agent的智能问答，支持图文混排文档的深度理解"
          >
            智能问答
          </Header>
        }
      >
        <SpaceBetween size="m">
          <FormField label="选择知识库">
            <Select
              selectedOption={
                kbId
                  ? {
                      value: kbId,
                      label:
                        knowledgeBases.find((kb) => kb.id === kbId)?.name ||
                        kbId,
                    }
                  : null
              }
              onChange={({ detail }) => {
                setKbId(detail.selectedOption.value || '');
              }}
              options={knowledgeBases.map((kb) => ({
                value: kb.id,
                label: kb.name,
              }))}
              placeholder="请选择知识库"
              empty="暂无知识库"
            />
          </FormField>

          <FormField
            label="提出问题"
            description="例如：登录注册模块的演进历史是怎样的？"
          >
            <Input
              value={query}
              onChange={({ detail }) => setQuery(detail.value)}
              placeholder="输入您的问题..."
              onKeyDown={(e) => {
                if (e.detail.key === 'Enter' && !isQuerying) {
                  handleQuery();
                }
              }}
              disabled={isQuerying}
            />
          </FormField>

          <Box textAlign="center">
            <Button
              variant="primary"
              onClick={handleQuery}
              loading={isQuerying}
              disabled={!query.trim() || !kbId}
            >
              {isQuerying ? '正在思考...' : '提问'}
            </Button>
          </Box>
        </SpaceBetween>
      </Container>

      {/* 状态提示 */}
      {status && !error && (
        <Alert type={isQuerying ? 'info' : 'success'} dismissible={false}>
          <SpaceBetween direction="horizontal" size="xs">
            {isQuerying && <Spinner />}
            <Box>{status}</Box>
          </SpaceBetween>
        </Alert>
      )}

      {/* 错误提示 */}
      {error && (
        <Alert type="error" dismissible onDismiss={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* 答案展示区 */}
      {answer && (
        <Container
          header={
            <Header
              variant="h2"
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Box variant="awsui-key-label">
                    Tokens: {formatTokens(metrics.total_tokens)}
                  </Box>
                  <Box variant="awsui-key-label">
                    耗时: {formatTime(metrics.response_time_ms)}
                  </Box>
                </SpaceBetween>
              }
            >
              答案
            </Header>
          }
        >
          <div ref={answerRef} className="markdown-content">
            <ReactMarkdown>
              {answer}
            </ReactMarkdown>
          </div>
        </Container>
      )}

      {/* 引用展示区 */}
      {citations.length > 0 && (
        <Container
          header={
            <Header variant="h2" counter={`(${citations.length})`}>
              引用来源
            </Header>
          }
        >
          <ColumnLayout columns={2} variant="default">
            {citations.map((citation, index) => (
              <div
                key={citation.chunk_id}
                className="citation-card"
                style={{
                  padding: '16px',
                  borderRadius: '8px',
                  border: '1px solid #d5dbdb',
                }}
              >
                <SpaceBetween size="s">
                  <Box>
                    <Box variant="strong">
                      引用 {index + 1} - {citation.document_name}
                    </Box>
                    <Box fontSize="body-s" color="text-body-secondary">
                      {citation.chunk_type === 'text' ? '文本' : '图片'} | 位置: {citation.chunk_index + 1}
                    </Box>
                  </Box>

                  {citation.chunk_type === 'text' && citation.content && (
                    <Box
                      padding="s"
                    >
                      <div className="markdown-content" style={{
                        backgroundColor: '#f4f4f4',
                        padding: '8px',
                        borderRadius: '4px',
                      }}>
                        <ReactMarkdown>
                          {citation.content}
                        </ReactMarkdown>
                      </div>
                    </Box>
                  )}

                  {citation.chunk_type === 'image' && citation.image_url && (
                    <Box>
                      <img
                        src={citation.image_url}
                        alt={citation.content || '图片'}
                        style={{
                          maxWidth: '100%',
                          height: 'auto',
                          borderRadius: '4px',
                        }}
                      />
                      {citation.content && (
                        <Box
                          fontSize="body-s"
                          color="text-body-secondary"
                          padding={{ top: 's' }}
                        >
                          {citation.content}
                        </Box>
                      )}
                    </Box>
                  )}
                </SpaceBetween>
              </div>
            ))}
          </ColumnLayout>
        </Container>
      )}

      {/* Token统计 */}
      {metrics.total_tokens > 0 && (
        <Container header={<Header variant="h3">Token统计</Header>}>
          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">输入Tokens</Box>
              <Box variant="p">{formatTokens(metrics.prompt_tokens)}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">输出Tokens</Box>
              <Box variant="p">{formatTokens(metrics.completion_tokens)}</Box>
            </div>
            <div>
              <Box variant="awsui-key-label">总计Tokens</Box>
              <Box variant="p">{formatTokens(metrics.total_tokens)}</Box>
            </div>
          </ColumnLayout>
        </Container>
      )}

      {/* 使用提示 */}
      {!answer && !isQuerying && (
        <Container
          header={<Header variant="h2">使用提示</Header>}
        >
          <SpaceBetween size="s">
            <Box variant="p">
              <strong>Multi-Agent架构：</strong>
              系统使用多个Agent协作回答问题。Sub-Agent深度阅读完整文档（包括图片），
              Main-Agent综合所有信息生成答案。
            </Box>
            <Box variant="p">
              <strong>支持的问题类型：</strong>
            </Box>
            <ul>
              <li>文档内容总结（例如：登录模块的功能需求有哪些？）</li>
              <li>跨文档演进历史（例如：支付功能是如何迭代的？）</li>
              <li>图文混排理解（例如：用户流程图是怎样的？）</li>
              <li>细节定位（例如：API接口的鉴权方式是什么？）</li>
            </ul>
            <Box variant="p">
              <strong>实时流式输出：</strong>
              答案会实时逐字生成，无需等待完整结果。引用来源会在答案生成完成后展示。
            </Box>
          </SpaceBetween>
        </Container>
      )}
    </SpaceBetween>
  );
}

export default function QueryPage() {
  return (
    <Suspense fallback={<Container><Box>加载中...</Box></Container>}>
      <QueryPageContent />
    </Suspense>
  );
}
