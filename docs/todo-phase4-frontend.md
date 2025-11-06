# Phase 4: 前端开发

> 预计工期：2周
> 目标：实现用户界面和交互

---

## 第1周：页面开发

### 1.1 项目初始化和布局 (Day 1)

- [ ] **安装Cloudscape组件库**
  ```bash
  cd frontend
  npm install @cloudscape-design/components
  npm install @cloudscape-design/global-styles
  npm install @cloudscape-design/collection-hooks
  ```

- [ ] **创建主布局**
  ```tsx
  // src/app/layout.tsx

  import '@cloudscape-design/global-styles/index.css'
  import TopNavigation from '@cloudscape-design/components/top-navigation'
  import SideNavigation from '@cloudscape-design/components/side-navigation'

  export default function RootLayout({
    children,
  }: {
    children: React.ReactNode
  }) {
    return (
      <html lang="zh-CN">
        <body>
          <div className="app-layout">
            <TopNavigation
              identity={{
                href: "/",
                title: "ASK-PRD"
              }}
              utilities={[
                {
                  type: "button",
                  text: "文档",
                  href: "/docs"
                }
              ]}
            />
            <div className="app-content">
              <SideNavigation
                items={[
                  { type: "link", text: "知识库", href: "/knowledge-bases" },
                  { type: "link", text: "文档管理", href: "/documents" },
                  { type: "link", text: "检索问答", href: "/query" }
                ]}
              />
              <main className="main-content">
                {children}
              </main>
            </div>
          </div>
        </body>
      </html>
    )
  }
  ```

- [ ] **创建API服务封装**
  ```tsx
  // src/services/api.ts

  import axios from 'axios'

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

  export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json'
    }
  })

  // 知识库API
  export const knowledgeBaseAPI = {
    list: () => api.get('/knowledge-bases'),
    create: (data: any) => api.post('/knowledge-bases', data),
    get: (id: string) => api.get(`/knowledge-bases/${id}`),
    delete: (id: string) => api.delete(`/knowledge-bases/${id}`)
  }

  // 文档API
  export const documentAPI = {
    list: (kbId: string, params?: any) =>
      api.get(`/knowledge-bases/${kbId}/documents`, { params }),
    upload: (kbId: string, file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      return api.post(`/knowledge-bases/${kbId}/documents/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    },
    delete: (kbId: string, docIds: string[]) =>
      api.delete(`/knowledge-bases/${kbId}/documents`, { data: { document_ids: docIds } })
  }

  // 同步任务API
  export const syncTaskAPI = {
    create: (kbId: string, data: any) =>
      api.post(`/knowledge-bases/${kbId}/sync`, data),
    list: (kbId: string, params?: any) =>
      api.get(`/knowledge-bases/${kbId}/sync-tasks`, { params }),
    get: (taskId: string) => api.get(`/sync-tasks/${taskId}`)
  }

  // 查询API (SSE在组件中单独处理)
  export const queryAPI = {
    history: (kbId: string, params?: any) =>
      api.get(`/knowledge-bases/${kbId}/query-history`, { params }),
    get: (queryId: string) => api.get(`/query-history/${queryId}`)
  }
  ```

### 1.2 知识库管理页面 (Day 2-3)

- [ ] **知识库列表页面**
  ```tsx
  // src/app/knowledge-bases/page.tsx

  'use client'

  import { useState, useEffect } from 'react'
  import Table from '@cloudscape-design/components/table'
  import Button from '@cloudscape-design/components/button'
  import Header from '@cloudscape-design/components/header'
  import { knowledgeBaseAPI } from '@/services/api'

  export default function KnowledgeBasesPage() {
    const [knowledgeBases, setKnowledgeBases] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
      loadKnowledgeBases()
    }, [])

    const loadKnowledgeBases = async () => {
      try {
        const response = await knowledgeBaseAPI.list()
        setKnowledgeBases(response.data.data)
      } catch (error) {
        console.error('Failed to load knowledge bases', error)
      } finally {
        setLoading(false)
      }
    }

    return (
      <Table
        header={
          <Header
            actions={
              <Button variant="primary" onClick={() => setCreateModalVisible(true)}>
                创建知识库
              </Button>
            }
          >
            知识库列表
          </Header>
        }
        loading={loading}
        items={knowledgeBases}
        columnDefinitions={[
          {
            id: 'name',
            header: '名称',
            cell: item => item.name
          },
          {
            id: 'description',
            header: '描述',
            cell: item => item.description
          },
          {
            id: 'document_count',
            header: '文档数',
            cell: item => item.document_count
          },
          {
            id: 'created_at',
            header: '创建时间',
            cell: item => new Date(item.created_at).toLocaleString()
          },
          {
            id: 'actions',
            header: '操作',
            cell: item => (
              <Button onClick={() => handleDelete(item.id)}>删除</Button>
            )
          }
        ]}
      />
    )
  }
  ```

- [ ] **创建知识库Modal**
  ```tsx
  // src/components/knowledge-base/CreateKnowledgeBaseModal.tsx

  import Modal from '@cloudscape-design/components/modal'
  import Form from '@cloudscape-design/components/form'
  import FormField from '@cloudscape-design/components/form-field'
  import Input from '@cloudscape-design/components/input'
  import Button from '@cloudscape-design/components/button'

  export default function CreateKnowledgeBaseModal({ visible, onClose, onSuccess }) {
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [s3Bucket, setS3Bucket] = useState('')
    const [s3Prefix, setS3Prefix] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async () => {
      setLoading(true)
      try {
        await knowledgeBaseAPI.create({
          name,
          description,
          s3_bucket: s3Bucket,
          s3_prefix: s3Prefix
        })
        onSuccess()
        onClose()
      } catch (error) {
        console.error('Failed to create knowledge base', error)
      } finally {
        setLoading(false)
      }
    }

    return (
      <Modal
        visible={visible}
        onDismiss={onClose}
        header="创建知识库"
        footer={
          <Box float="right">
            <Button variant="link" onClick={onClose}>取消</Button>
            <Button variant="primary" onClick={handleSubmit} loading={loading}>
              创建
            </Button>
          </Box>
        }
      >
        <Form>
          <FormField label="知识库名称" constraintText="必填">
            <Input value={name} onChange={e => setName(e.detail.value)} />
          </FormField>
          <FormField label="描述">
            <Input value={description} onChange={e => setDescription(e.detail.value)} />
          </FormField>
          <FormField label="S3桶名" constraintText="必填">
            <Input value={s3Bucket} onChange={e => setS3Bucket(e.detail.value)} />
          </FormField>
          <FormField label="S3路径前缀" constraintText="必填，以/结尾">
            <Input value={s3Prefix} onChange={e => setS3Prefix(e.detail.value)} />
          </FormField>
        </Form>
      </Modal>
    )
  }
  ```

### 1.3 文档管理页面 (Day 3-4)

- [ ] **文档列表页面**
  ```tsx
  // src/app/documents/page.tsx

  'use client'

  import { useState, useEffect } from 'react'
  import Table from '@cloudscape-design/components/table'
  import Select from '@cloudscape-design/components/select'
  import Button from '@cloudscape-design/components/button'
  import Header from '@cloudscape-design/components/header'
  import SpaceBetween from '@cloudscape-design/components/space-between'

  export default function DocumentsPage() {
    const [selectedKb, setSelectedKb] = useState(null)
    const [documents, setDocuments] = useState([])
    const [selectedDocs, setSelectedDocs] = useState([])

    const handleUpload = () => {
      // 打开上传Modal
    }

    const handleSync = async () => {
      if (!selectedKb) return
      try {
        await syncTaskAPI.create(selectedKb.value, {
          task_type: 'full_sync',
          document_ids: []
        })
        alert('同步任务已创建')
      } catch (error) {
        console.error('Failed to create sync task', error)
      }
    }

    const handleDelete = async () => {
      if (selectedDocs.length === 0) return
      try {
        await documentAPI.delete(
          selectedKb.value,
          selectedDocs.map(d => d.id)
        )
        loadDocuments()
      } catch (error) {
        console.error('Failed to delete documents', error)
      }
    }

    return (
      <SpaceBetween size="l">
        <Header
          variant="h1"
          actions={
            <Select
              selectedOption={selectedKb}
              onChange={e => setSelectedKb(e.detail.selectedOption)}
              options={knowledgeBaseOptions}
              placeholder="选择知识库"
            />
          }
        >
          文档管理
        </Header>

        <Table
          header={
            <Header
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={handleUpload}>上传文档</Button>
                  <Button onClick={handleSync}>数据同步</Button>
                  <Button onClick={handleDelete} disabled={selectedDocs.length === 0}>
                    删除
                  </Button>
                </SpaceBetween>
              }
            >
              文档列表
            </Header>
          }
          selectionType="multi"
          selectedItems={selectedDocs}
          onSelectionChange={e => setSelectedDocs(e.detail.selectedItems)}
          items={documents}
          columnDefinitions={[
            {
              id: 'filename',
              header: '文件名',
              cell: item => item.filename
            },
            {
              id: 'status',
              header: '状态',
              cell: item => <StatusIndicator type={getStatusType(item.status)}>
                {getStatusText(item.status)}
              </StatusIndicator>
            },
            {
              id: 'file_size',
              header: '文件大小',
              cell: item => formatFileSize(item.file_size)
            },
            {
              id: 'page_count',
              header: '页数',
              cell: item => item.page_count
            },
            {
              id: 'created_at',
              header: '上传时间',
              cell: item => new Date(item.created_at).toLocaleString()
            }
          ]}
        />
      </SpaceBetween>
    )
  }
  ```

- [ ] **文档上传组件**
  ```tsx
  // src/components/document/DocumentUploadModal.tsx

  import FileUpload from '@cloudscape-design/components/file-upload'

  export default function DocumentUploadModal({ visible, kbId, onClose, onSuccess }) {
    const [files, setFiles] = useState([])
    const [uploading, setUploading] = useState(false)

    const handleUpload = async () => {
      if (files.length === 0) return

      setUploading(true)
      try {
        for (const file of files) {
          await documentAPI.upload(kbId, file)
        }
        onSuccess()
        onClose()
      } catch (error) {
        console.error('Failed to upload documents', error)
      } finally {
        setUploading(false)
      }
    }

    return (
      <Modal visible={visible} onDismiss={onClose} header="上传文档">
        <FileUpload
          value={files}
          onChange={e => setFiles(e.detail.value)}
          accept=".pdf"
          multiple
          constraintText="仅支持PDF格式，单个文件最大100MB"
        />
        <Box float="right" margin={{ top: 'm' }}>
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={onClose}>取消</Button>
            <Button variant="primary" onClick={handleUpload} loading={uploading}>
              上传
            </Button>
          </SpaceBetween>
        </Box>
      </Modal>
    )
  }
  ```

---

## 第2周：问答界面和优化

### 2.1 检索问答页面 (Day 5-7)

- [ ] **问答主页面**
  ```tsx
  // src/app/query/page.tsx

  'use client'

  import { useState } from 'react'
  import Container from '@cloudscape-design/components/container'
  import Textarea from '@cloudscape-design/components/textarea'
  import Button from '@cloudscape-design/components/button'
  import SpaceBetween from '@cloudscape-design/components/space-between'

  export default function QueryPage() {
    const [query, setQuery] = useState('')
    const [selectedKb, setSelectedKb] = useState(null)
    const [answer, setAnswer] = useState('')
    const [citations, setCitations] = useState([])
    const [loading, setLoading] = useState(false)

    const handleQuery = async () => {
      if (!query || !selectedKb) return

      setLoading(true)
      setAnswer('')
      setCitations([])

      try {
        // 使用EventSource处理SSE
        const eventSource = new EventSource(
          `${API_BASE_URL}/knowledge-bases/${selectedKb.value}/query/stream`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
          }
        )

        eventSource.addEventListener('chunk', (e) => {
          const data = JSON.parse(e.data)
          setAnswer(prev => prev + data.content)
        })

        eventSource.addEventListener('citation', (e) => {
          const citation = JSON.parse(e.data)
          setCitations(prev => [...prev, citation])
        })

        eventSource.addEventListener('done', (e) => {
          eventSource.close()
          setLoading(false)
        })

        eventSource.addEventListener('error', (e) => {
          console.error('SSE error', e)
          eventSource.close()
          setLoading(false)
        })

      } catch (error) {
        console.error('Query failed', error)
        setLoading(false)
      }
    }

    return (
      <Container>
        <SpaceBetween size="l">
          {/* 知识库选择 */}
          <Select
            selectedOption={selectedKb}
            onChange={e => setSelectedKb(e.detail.selectedOption)}
            options={knowledgeBaseOptions}
            placeholder="选择知识库"
          />

          {/* 搜索框 */}
          <Textarea
            value={query}
            onChange={e => setQuery(e.detail.value)}
            placeholder="请输入您的问题..."
            rows={3}
          />

          <Button
            variant="primary"
            onClick={handleQuery}
            loading={loading}
            disabled={!query || !selectedKb}
          >
            提问
          </Button>

          {/* 答案展示 */}
          {answer && (
            <AnswerDisplay answer={answer} citations={citations} />
          )}
        </SpaceBetween>
      </Container>
    )
  }
  ```

- [ ] **答案展示组件**
  ```tsx
  // src/components/query/AnswerDisplay.tsx

  import ReactMarkdown from 'react-markdown'
  import Container from '@cloudscape-design/components/container'
  import Header from '@cloudscape-design/components/header'

  export default function AnswerDisplay({ answer, citations }) {
    return (
      <Container header={<Header>答案</Header>}>
        <div className="markdown-content">
          <ReactMarkdown>{answer}</ReactMarkdown>
        </div>

        {citations.length > 0 && (
          <div className="citations">
            <h3>引用来源</h3>
            {citations.map((citation, index) => (
              <CitationCard key={index} citation={citation} index={index + 1} />
            ))}
          </div>
        )}
      </Container>
    )
  }
  ```

- [ ] **引用卡片组件**
  ```tsx
  // src/components/query/CitationCard.tsx

  import Container from '@cloudscape-design/components/container'
  import Box from '@cloudscape-design/components/box'

  export default function CitationCard({ citation, index }) {
    if (citation.chunk_type === 'text') {
      return (
        <Container>
          <Box variant="awsui-key-label">
            [{index}] {citation.document_name}
          </Box>
          <Box variant="p">{citation.content}</Box>
        </Container>
      )
    } else {
      return (
        <Container>
          <Box variant="awsui-key-label">
            [{index}] {citation.document_name} - 图片
          </Box>
          <img
            src={citation.image_url}
            alt={citation.image_description}
            style={{ maxWidth: '100%', marginTop: '8px' }}
          />
          <Box variant="small" margin={{ top: 'xs' }}>
            {citation.image_description}
          </Box>
        </Container>
      )
    }
  }
  ```

### 2.2 历史记录侧边栏 (Day 7-8)

- [ ] **历史记录组件**
  ```tsx
  // src/components/query/QueryHistory.tsx

  import SideNavigation from '@cloudscape-design/components/side-navigation'

  export default function QueryHistory({ kbId, onSelect }) {
    const [history, setHistory] = useState([])

    useEffect(() => {
      if (kbId) {
        loadHistory()
      }
    }, [kbId])

    const loadHistory = async () => {
      try {
        const response = await queryAPI.history(kbId, { page_size: 50 })
        setHistory(response.data.data)
      } catch (error) {
        console.error('Failed to load history', error)
      }
    }

    return (
      <SideNavigation
        header={{ text: '历史记录' }}
        items={history.map(item => ({
          type: 'link',
          text: truncate(item.query_text, 30),
          href: '#',
          info: new Date(item.created_at).toLocaleString(),
          onClick: (e) => {
            e.preventDefault()
            onSelect(item.id)
          }
        }))}
      />
    )
  }
  ```

### 2.3 同步任务进度监控 (Day 9)

- [ ] **任务进度组件**
  ```tsx
  // src/components/document/SyncTaskMonitor.tsx

  import ProgressBar from '@cloudscape-design/components/progress-bar'
  import StatusIndicator from '@cloudscape-design/components/status-indicator'

  export default function SyncTaskMonitor({ taskId }) {
    const [task, setTask] = useState(null)

    useEffect(() => {
      if (!taskId) return

      // 轮询任务状态
      const interval = setInterval(async () => {
        try {
          const response = await syncTaskAPI.get(taskId)
          setTask(response.data.data)

          // 如果任务完成，停止轮询
          if (['completed', 'failed', 'partial_success'].includes(response.data.data.status)) {
            clearInterval(interval)
          }
        } catch (error) {
          console.error('Failed to get task status', error)
          clearInterval(interval)
        }
      }, 2000)  // 每2秒轮询一次

      return () => clearInterval(interval)
    }, [taskId])

    if (!task) return null

    return (
      <Container>
        <SpaceBetween size="m">
          <StatusIndicator type={getTaskStatusType(task.status)}>
            {getTaskStatusText(task.status)}
          </StatusIndicator>

          <ProgressBar
            value={task.progress}
            label="进度"
            description={task.current_step}
          />

          <div>
            <Box variant="awsui-key-label">总文档数</Box>
            <Box>{task.total_documents}</Box>
          </div>
          <div>
            <Box variant="awsui-key-label">已处理</Box>
            <Box>{task.processed_documents}</Box>
          </div>
          <div>
            <Box variant="awsui-key-label">失败</Box>
            <Box>{task.failed_documents}</Box>
          </div>
        </SpaceBetween>
      </Container>
    )
  }
  ```

### 2.4 样式和优化 (Day 10)

- [ ] **自定义CSS样式**
  ```css
  /* src/app/globals.css */

  .markdown-content {
    line-height: 1.8;
    font-size: 14px;
  }

  .markdown-content h1,
  .markdown-content h2,
  .markdown-content h3 {
    margin-top: 1.5em;
    margin-bottom: 0.75em;
  }

  .markdown-content code {
    background-color: #f5f5f5;
    padding: 2px 6px;
    border-radius: 3px;
  }

  .citations {
    margin-top: 2em;
    padding-top: 1em;
    border-top: 1px solid #e5e5e5;
  }

  .citation-card {
    margin-bottom: 1em;
  }
  ```

- [ ] **响应式布局优化**
  - 适配桌面和平板
  - 侧边栏可折叠
  - 图片自适应

- [ ] **加载状态优化**
  - Skeleton加载效果
  - 流式输出动画
  - 错误提示优化

---

## 验收标准

### 必须完成
- [ ] 知识库列表可以正常展示
- [ ] 可以创建和删除知识库
- [ ] 文档列表可以正常展示
- [ ] 可以上传文档
- [ ] 可以触发数据同步
- [ ] 可以查看同步任务进度
- [ ] 可以进行问答
- [ ] 答案流式展示正常
- [ ] 引用可以正确展示（文本+图片）
- [ ] 历史记录可以查看
- [ ] UI美观，交互流畅

### 可选
- [ ] 移动端适配
- [ ] 暗黑模式
- [ ] 快捷键支持

---

## 检查清单

- [ ] 所有页面开发完成
- [ ] 所有API调用正常
- [ ] SSE流式输出正常
- [ ] 图片可以正确展示
- [ ] 错误提示友好
- [ ] 加载状态清晰
- [ ] 响应式布局正常
- [ ] 浏览器兼容性测试通过
- [ ] 性能可接受（无明显卡顿）

---

## 下一步

完成Phase 4后，进入 [Phase 5: 测试和优化](./todo-phase5-testing.md)
