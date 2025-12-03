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
import { authService } from '@/services/auth';
import { knowledgeBaseAPI, queryAPI } from '@/services/api';
import type { KnowledgeBase, CitationItem, QueryStreamEvent } from '@/types';

// 自定义图片渲染组件，支持带Token的请求
function AuthenticatedImage({ src, alt }: { src?: string; alt?: string }) {
  const [imageSrc, setImageSrc] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!src) return;

    // 如果是外部链接，直接使用
    if (src.startsWith('http://') || src.startsWith('https://')) {
      setImageSrc(src);
      setLoading(false);
      return;
    }

    // 如果是内部API链接，带Token请求
    const fetchImage = async () => {
      try {
        const token = authService.getToken();
        const response = await fetch(src, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });

        if (!response.ok) {
          throw new Error('Failed to load image');
        }

        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        setImageSrc(objectUrl);
        setLoading(false);
      } catch (err) {
        console.error('Failed to load image:', err);
        setError(true);
        setLoading(false);
      }
    };

    fetchImage();

    // 清理object URL
    return () => {
      if (imageSrc && imageSrc.startsWith('blob:')) {
        URL.revokeObjectURL(imageSrc);
      }
    };
  }, [src]);

  if (loading) {
    return <Spinner size="normal" />;
  }

  if (error) {
    return <Box color="text-status-error">图片加载失败</Box>;
  }

  return (
    <img
      src={imageSrc}
      alt={alt || '图片'}
      style={{ maxWidth: '100%', height: 'auto', borderRadius: '4px' }}
    />
  );
}

function QueryPageContent() {
  const searchParams = useSearchParams();
  const [kbId, setKbId] = useState<string>(searchParams.get('kb_id') || '');
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [query, setQuery] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [answer, setAnswer] = useState('');
  const [citations, setCitations] = useState<CitationItem[]>([]);
  const [processedAnswer, setProcessedAnswer] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
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

  // 处理答案中的图片引用标记，替换为实际的Markdown图片语法
  useEffect(() => {
    if (!answer) {
      setProcessedAnswer('');
      return;
    }

    let processed = answer;

    // 如果有citations数据，替换图片标记
    if (citations.length > 0) {
      citations.forEach((citation) => {
        if (citation.chunk_type === 'image' && citation.image_url) {
          // 将 [DOC-xxx-IMAGE-X] 替换为 ![图片](url)
          const pattern = new RegExp(`\\[${citation.chunk_id}\\]`, 'g');
          const imageAlt = citation.content || '图片';
          processed = processed.replace(pattern, `![${imageAlt}](${citation.image_url})`);
        }
      });
    }

    setProcessedAnswer(processed);
  }, [answer, citations]);

  // 处理SSE流式输出
  const handleQuery = async () => {
    if (!query.trim() || !kbId) return;

    // 重置状态
    setIsQuerying(true);
    setAnswer('');
    setCitations([]);
    setStatus('正在处理...');
    setError('');

    try {
      const stream = await queryAPI.stream(kbId, query.trim());
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        let result;
        try {
          result = await reader.read();
        } catch (readError) {
          console.error('Stream read error:', readError);
          // 流读取错误，可能是连接中断
          setStatus('连接中断');
          break;
        }

        const { done, value } = result;
        if (done) {
          // 流正常结束
          break;
        }

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
              } else if (data.type === 'heartbeat') {
                // 心跳事件，更新状态（保持连接活跃）
                setStatus((data as any).message || '正在生成中...');
              } else if (data.type === 'chunk') {
                // Multi-Agent系统的事件类型：chunk，字段名是 content
                setAnswer((prev) => prev + (data as any).content);
                // 自动滚动到底部
                setTimeout(() => {
                  answerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
                }, 0);
              } else if (data.type === 'answer_delta') {
                // Two-Stage系统的事件类型：answer_delta，字段在 data.text
                const textChunk = (data as any).data?.text || '';
                setAnswer((prev) => prev + textChunk);
                // 自动滚动到底部
                setTimeout(() => {
                  answerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
                }, 0);
              } else if (data.type === 'answer_complete') {
                // 答案生成完成，包含后处理后的完整markdown（图片路径已转换）
                const completeText = (data as any).data?.text || '';
                setAnswer(completeText);
                // 自动滚动到底部
                setTimeout(() => {
                  answerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
                }, 0);
              } else if (data.type === 'progress') {
                // Two-Stage系统的进度事件
                const progressData = (data as any).data;
                const statusText = progressData.status === 'failed'
                  ? `已完成 ${progressData.completed}/${progressData.total} 个文档（失败: ${progressData.doc_name}）`
                  : `已完成 ${progressData.completed}/${progressData.total} 个文档: ${progressData.doc_name}`;
                setStatus(statusText);
              } else if (data.type === 'retrieved_documents') {
                // Two-Stage系统的文档检索事件
                const docData = (data as any);
                setStatus(`已检索到 ${docData.document_count} 个相关文档`);
              } else if (data.type === 'references') {
                // Two-Stage系统的引用事件（批量）
                const refs = (data as any).data || [];
                // 将Two-Stage的Reference格式转换为前端的CitationItem格式
                const newCitations = refs.map((ref: any) => ({
                  chunk_id: ref.ref_id,
                  chunk_type: ref.chunk_type,
                  document_id: ref.doc_id,
                  document_name: ref.doc_name,
                  chunk_index: parseInt(ref.ref_id.split('-').pop() || '0') - 1,
                  content: ref.content,
                  image_url: ref.image_url,
                }));
                setCitations(newCitations);
              } else if (data.type === 'citation') {
                // Multi-Agent系统的引用事件（单个）
                setCitations((prev) => [...prev, data as any]);
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

      // 流正常结束，确保状态更新
      if (status === '正在处理...') {
        setStatus('完成');
      }
    } catch (error: any) {
      console.error('Query error:', error);
      setError(error.message || '查询失败');
      setStatus('错误');
    } finally {
      // 确保总是停止loading状态
      setIsQuerying(false);
    }
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
          header={<Header variant="h2">答案</Header>}
        >
          <div ref={answerRef} className="markdown-content">
            <ReactMarkdown
              components={{
                img: ({ node, ...props }) => (
                  <AuthenticatedImage
                    src={typeof props.src === 'string' ? props.src : undefined}
                    alt={typeof props.alt === 'string' ? props.alt : undefined}
                  />
                ),
              }}
            >
              {processedAnswer || answer}
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
                        <ReactMarkdown
                          components={{
                            img: ({ node, ...props }) => (
                              <AuthenticatedImage
                                src={typeof props.src === 'string' ? props.src : undefined}
                                alt={typeof props.alt === 'string' ? props.alt : undefined}
                              />
                            ),
                          }}
                        >
                          {citation.content}
                        </ReactMarkdown>
                      </div>
                    </Box>
                  )}

                  {citation.chunk_type === 'image' && citation.image_url && (
                    <Box>
                      <AuthenticatedImage
                        src={citation.image_url}
                        alt={citation.content || '图片'}
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
