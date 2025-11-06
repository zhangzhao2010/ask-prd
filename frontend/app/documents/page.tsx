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

  // 加载同步任务列表
  const loadSyncTasks = async () => {
    if (!kbId) return;

    try {
      const response = await syncTaskAPI.list({
        kb_id: kbId,
        page: 1,
        page_size: 5,
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
      // 轮询同步任务状态
      const interval = setInterval(loadSyncTasks, 3000);
      return () => clearInterval(interval);
    }
  }, [kbId, currentPage]);

  // 过滤文档
  const filteredDocuments = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(filterText.toLowerCase())
  );

  // 上传文档
  const handleUpload = async () => {
    if (uploadFiles.length === 0 || !kbId) return;

    setUploading(true);
    try {
      // 上传所有文件
      await Promise.all(
        uploadFiles.map((file) => documentAPI.upload(kbId, file))
      );

      // 创建同步任务
      await syncTaskAPI.create({
        kb_id: kbId,
        task_type: 'incremental',
      });

      setUploadModalVisible(false);
      setUploadFiles([]);
      loadDocuments();
      loadSyncTasks();
    } catch (error) {
      console.error('Failed to upload documents:', error);
    } finally {
      setUploading(false);
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
      processing: { text: '处理中', color: 'in-progress' },
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
      {syncTasks.length > 0 && (
        <Container header={<Header variant="h2">同步任务</Header>}>
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
              id: 's3_key',
              header: 'S3路径',
              cell: (item) => (
                <Box fontSize="body-s" color="text-body-secondary">
                  {item.s3_key}
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
            上传后会自动创建同步任务，开始转换和向量化处理。
            可以在"同步任务"区域查看进度。
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
