'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  Container,
  Header,
  SpaceBetween,
  Button,
  Table,
  Box,
  TextFilter,
  Pagination,
  Badge,
  Modal,
  FileUpload,
  FormField,
  Select,
  ProgressBar,
  Alert,
} from '@cloudscape-design/components';
import { documentAPI, syncTaskAPI, knowledgeBaseAPI } from '@/services/api';
import type { Document, SyncTask, KnowledgeBase } from '@/types';

function DocumentsPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [kbId, setKbId] = useState<string>(searchParams.get('kb_id') || '');
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [syncTasks, setSyncTasks] = useState<SyncTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItems, setSelectedItems] = useState<Document[]>([]);
  const [filterText, setFilterText] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [syncModalVisible, setSyncModalVisible] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string>('');

  // 加载知识库列表
  const loadKnowledgeBases = async () => {
    try {
      const response = await knowledgeBaseAPI.list({ page: 1, page_size: 100 });
      setKnowledgeBases(response.items);
    } catch (error) {
      console.error('Failed to load knowledge bases:', error);
    }
  };

  // 加载文档列表
  const loadDocuments = async () => {
    if (!kbId) return;

    setLoading(true);
    try {
      const response = await documentAPI.list({
        kb_id: kbId,
        page: currentPage,
        page_size: 10,
      });
      setDocuments(response.items);
      setTotalPages(response.meta.total_pages);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
    }
  };

  // 加载同步任务列表（只显示最新一条）
  const loadSyncTasks = async () => {
    if (!kbId) return;

    try {
      const response = await syncTaskAPI.list({
        kb_id: kbId,
        limit: 1,  // 只获取最新的一条任务
      });
      setSyncTasks(response.items);
    } catch (error) {
      console.error('Failed to load sync tasks:', error);
    }
  };

  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  useEffect(() => {
    if (kbId) {
      loadDocuments();
      loadSyncTasks();
    }
  }, [kbId, currentPage]);

  // 过滤文档
  const filteredDocuments = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(filterText.toLowerCase())
  );

  // 上传文档（仅上传到S3，不触发同步）
  const handleUpload = async () => {
    if (uploadFiles.length === 0 || !kbId) return;

    setUploading(true);
    try {
      // 上传所有文件到S3
      await Promise.all(
        uploadFiles.map((file) => documentAPI.upload(kbId, file))
      );

      setUploadModalVisible(false);
      setUploadFiles([]);
      loadDocuments();
    } catch (error) {
      console.error('Failed to upload documents:', error);
    } finally {
      setUploading(false);
    }
  };

  // 触发数据同步
  const handleSync = async () => {
    if (!kbId) return;

    setSyncing(true);
    setSyncError('');
    try {
      await syncTaskAPI.create({
        kb_id: kbId,
        task_type: 'full_sync',
      });

      setSyncModalVisible(false);
      loadSyncTasks();
    } catch (error: any) {
      console.error('Failed to create sync task:', error);
      // 提取后端返回的错误信息
      // 注意：axios拦截器已经提取了error.response.data，所以直接访问error.message
      const errorMessage = error?.message || '创建同步任务失败';
      setSyncError(errorMessage);
    } finally {
      setSyncing(false);
    }
  };

  // 删除文档
  const handleDelete = async () => {
    if (selectedItems.length === 0) return;

    setDeleteLoading(true);
    try {
      await Promise.all(
        selectedItems.map((item) => documentAPI.delete(item.id))
      );
      setDeleteModalVisible(false);
      setSelectedItems([]);
      loadDocuments();
    } catch (error) {
      console.error('Failed to delete documents:', error);
    } finally {
      setDeleteLoading(false);
    }
  };

  // 状态Badge
  const statusBadge = (status: string) => {
    const statusMap: Record<string, { text: string; color: any }> = {
      uploaded: { text: '已上传', color: 'blue' },
      processing: { text: '处理中', color: 'blue' },
      completed: { text: '已完成', color: 'green' },
      failed: { text: '失败', color: 'red' },
    };
    const config = statusMap[status] || { text: status, color: 'grey' };
    return <Badge color={config.color}>{config.text}</Badge>;
  };

  // 同步任务状态Badge
  const taskStatusBadge = (status: string) => {
    const statusMap: Record<string, { text: string; color: any }> = {
      pending: { text: '等待中', color: 'grey' },
      running: { text: '运行中', color: 'blue' },
      completed: { text: '已完成', color: 'green' },
      failed: { text: '失败', color: 'red' },
      partial_success: { text: '部分成功', color: 'grey' },
    };
    const config = statusMap[status] || { text: status, color: 'grey' };
    return <Badge color={config.color}>{config.text}</Badge>;
  };

  // 格式化文件大小
  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <SpaceBetween size="l">
      {/* 知识库选择 */}
      <Container>
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
              setCurrentPage(1);
            }}
            options={knowledgeBases.map((kb) => ({
              value: kb.id,
              label: kb.name,
            }))}
            placeholder="请选择知识库"
            empty="暂无知识库"
          />
        </FormField>
      </Container>

      {/* 同步任务监控 */}
      {kbId && (
        <Container
          header={
            <Header
              variant="h2"
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={loadSyncTasks} iconName="refresh">
                    刷新
                  </Button>
                  <Button variant="primary" onClick={() => setSyncModalVisible(true)}>
                    同步数据
                  </Button>
                </SpaceBetween>
              }
            >
              同步任务
            </Header>
          }
        >
          {syncTasks.length > 0 ? (
            <SpaceBetween size="m">
              {syncTasks.map((task) => (
                <Box key={task.id}>
                  <SpaceBetween size="xs">
                    <Box>
                      <SpaceBetween direction="horizontal" size="xs">
                        <Box variant="strong">任务ID: {task.id}</Box>
                        {taskStatusBadge(task.status)}
                      </SpaceBetween>
                    </Box>
                    {task.status === 'running' && (
                      <ProgressBar
                        value={task.progress}
                        label={task.current_step || '处理中'}
                        description={`已处理: ${task.processed_documents}/${task.total_documents} | 失败: ${task.failed_documents}`}
                      />
                    )}
                    {task.status === 'completed' && (
                      <Alert type="success">
                        同步完成！处理了 {task.processed_documents} 个文档
                      </Alert>
                    )}
                    {task.status === 'failed' && (
                      <Alert type="error">
                        同步失败: {task.error_message}
                      </Alert>
                    )}
                  </SpaceBetween>
                </Box>
              ))}
            </SpaceBetween>
          ) : (
            <Box textAlign="center" color="inherit">
              <Box variant="p" color="text-body-secondary">
                暂无同步任务，点击"同步数据"按钮开始处理文档
              </Box>
            </Box>
          )}
        </Container>
      )}

      {/* 文档列表 */}
      <Container
        header={
          <Header
            variant="h1"
            description="上传和管理PRD文档，系统会自动转换为Markdown并提取图片"
            actions={
              <Button
                variant="primary"
                onClick={() => setUploadModalVisible(true)}
                disabled={!kbId}
              >
                上传文档
              </Button>
            }
          >
            文档管理
          </Header>
        }
      >
        <Table
          stickyHeader={false}
          loading={loading}
          selectedItems={selectedItems}
          onSelectionChange={({ detail }) => setSelectedItems(detail.selectedItems)}
          columnDefinitions={[
            {
              id: 'filename',
              header: '文件名',
              cell: (item) => item.filename,
              sortingField: 'filename',
            },
            {
              id: 'status',
              header: '状态',
              cell: (item) => statusBadge(item.status),
            },
            {
              id: 'file_size',
              header: '文件大小',
              cell: (item) => formatFileSize(item.file_size),
            },
            {
              id: 'page_count',
              header: '页数',
              cell: (item) => item.page_count || '-',
            },
            {
              id: 'local_path',
              header: '本地路径',
              cell: (item) => (
                <Box fontSize="body-s" color="text-body-secondary">
                  {item.local_pdf_path || '本地存储'}
                </Box>
              ),
            },
            {
              id: 'created_at',
              header: '上传时间',
              cell: (item) => new Date(item.created_at).toLocaleString('zh-CN'),
              sortingField: 'created_at',
            },
            {
              id: 'error',
              header: '错误信息',
              cell: (item) =>
                item.error_message ? (
                  <Box color="text-status-error" fontSize="body-s">
                    {item.error_message}
                  </Box>
                ) : (
                  '-'
                ),
            },
          ]}
          items={filteredDocuments}
          selectionType="multi"
          trackBy="id"
          empty={
            <Box textAlign="center" color="inherit">
              <b>暂无文档</b>
              <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                {kbId
                  ? '点击"上传文档"按钮开始上传PDF文件'
                  : '请先选择知识库'}
              </Box>
            </Box>
          }
          filter={
            <TextFilter
              filteringText={filterText}
              onChange={({ detail }) => setFilterText(detail.filteringText)}
              filteringPlaceholder="搜索文档"
            />
          }
          header={
            <Header
              counter={`(${filteredDocuments.length})`}
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={loadDocuments} iconName="refresh">
                    刷新
                  </Button>
                  <Button
                    onClick={() => setDeleteModalVisible(true)}
                    disabled={selectedItems.length === 0}
                  >
                    删除
                  </Button>
                </SpaceBetween>
              }
            >
              文档
            </Header>
          }
          pagination={
            <Pagination
              currentPageIndex={currentPage}
              pagesCount={totalPages}
              onChange={({ detail }) => setCurrentPage(detail.currentPageIndex)}
            />
          }
        />
      </Container>

      {/* 上传文档Modal */}
      <Modal
        visible={uploadModalVisible}
        onDismiss={() => setUploadModalVisible(false)}
        header="上传PDF文档"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={() => setUploadModalVisible(false)}>
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleUpload}
                loading={uploading}
                disabled={uploadFiles.length === 0}
              >
                上传
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween size="m">
          <FormField
            label="选择PDF文件"
            description="支持批量上传，系统会自动转换为Markdown并提取图片"
          >
            <FileUpload
              value={uploadFiles}
              onChange={({ detail }) => setUploadFiles(detail.value)}
              multiple
              accept=".pdf"
              i18nStrings={{
                uploadButtonText: (e) => (e ? '选择文件' : '选择文件'),
                dropzoneText: (e) => (e ? '拖放文件到这里' : '拖放文件到这里'),
                removeFileAriaLabel: (e) => `删除文件 ${e + 1}`,
                limitShowFewer: '显示更少文件',
                limitShowMore: '显示更多文件',
                errorIconAriaLabel: '错误',
              }}
            />
          </FormField>

          <Alert type="info">
            上传后文档将保存到S3，需要点击"同步数据"按钮触发转换和向量化处理。
          </Alert>
        </SpaceBetween>
      </Modal>

      {/* 同步数据Modal */}
      <Modal
        visible={syncModalVisible}
        onDismiss={() => {
          setSyncModalVisible(false);
          setSyncError('');
        }}
        header="同步数据"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="link"
                onClick={() => {
                  setSyncModalVisible(false);
                  setSyncError('');
                }}
              >
                取消
              </Button>
              <Button variant="primary" onClick={handleSync} loading={syncing}>
                开始同步
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween size="m">
          {syncError && (
            <Alert type="error" dismissible onDismiss={() => setSyncError('')}>
              {syncError}
            </Alert>
          )}
          <Box>
            将对知识库中状态为"已上传"的文档执行以下操作：
          </Box>
          <Box>
            <ul>
              <li>使用Marker将PDF转换为Markdown和图片</li>
              <li>使用Claude Vision API理解图片内容</li>
              <li>将文本和图片分块并向量化</li>
              <li>上传转换结果到S3并存储向量到OpenSearch</li>
            </ul>
          </Box>
          <Alert type="warning">
            同步过程可能需要较长时间，请在"同步任务"区域查看进度。
          </Alert>
        </SpaceBetween>
      </Modal>

      {/* 删除确认Modal */}
      <Modal
        visible={deleteModalVisible}
        onDismiss={() => setDeleteModalVisible(false)}
        header="确认删除"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={() => setDeleteModalVisible(false)}>
                取消
              </Button>
              <Button variant="primary" onClick={handleDelete} loading={deleteLoading}>
                删除
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <Box>
          确定要删除选中的 {selectedItems.length} 个文档吗？
          <br />
          <Box color="text-status-error" variant="p">
            警告：删除文档将同时删除其转换结果和向量数据，此操作不可恢复！
          </Box>
        </Box>
      </Modal>
    </SpaceBetween>
  );
}

export default function DocumentsPage() {
  return (
    <Suspense fallback={<Container><Box>加载中...</Box></Container>}>
      <DocumentsPageContent />
    </Suspense>
  );
}
