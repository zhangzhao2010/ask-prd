'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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
} from '@cloudscape-design/components';
import { knowledgeBaseAPI } from '@/services/api';
import type { KnowledgeBase } from '@/types';
import CreateKnowledgeBaseModal from '@/components/knowledge-base/CreateKnowledgeBaseModal';

export default function KnowledgeBasesPage() {
  const router = useRouter();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedItems, setSelectedItems] = useState<KnowledgeBase[]>([]);
  const [filterText, setFilterText] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // 加载知识库列表
  const loadKnowledgeBases = async () => {
    setLoading(true);
    try {
      const response = await knowledgeBaseAPI.list({
        page: currentPage,
        page_size: 10,
      });
      setKnowledgeBases(response.items);
      setTotalPages(response.meta.total_pages);
    } catch (error) {
      console.error('Failed to load knowledge bases:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadKnowledgeBases();
  }, [currentPage]);

  // 过滤知识库
  const filteredKnowledgeBases = knowledgeBases.filter((kb) =>
    kb.name.toLowerCase().includes(filterText.toLowerCase()) ||
    (kb.description && kb.description.toLowerCase().includes(filterText.toLowerCase()))
  );

  // 删除知识库
  const handleDelete = async () => {
    if (selectedItems.length === 0) return;

    setDeleteLoading(true);
    try {
      await Promise.all(
        selectedItems.map((item) => knowledgeBaseAPI.delete(item.id))
      );
      setDeleteModalVisible(false);
      setSelectedItems([]);
      loadKnowledgeBases();
    } catch (error) {
      console.error('Failed to delete knowledge base:', error);
    } finally {
      setDeleteLoading(false);
    }
  };

  // 状态Badge
  const statusBadge = (status: string) => {
    const statusMap: Record<string, { text: string; color: any }> = {
      active: { text: '已激活', color: 'green' },
      creating: { text: '创建中', color: 'blue' },
      failed: { text: '失败', color: 'red' },
    };
    const config = statusMap[status] || { text: status, color: 'grey' };
    return <Badge color={config.color}>{config.text}</Badge>;
  };

  return (
    <SpaceBetween size="l">
      <Container
        header={
          <Header
            variant="h1"
            description="管理PRD文档知识库，每个知识库对应一个独立的OpenSearch索引"
            actions={
              <Button
                variant="primary"
                onClick={() => setCreateModalVisible(true)}
              >
                创建知识库
              </Button>
            }
          >
            知识库列表
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
              id: 'name',
              header: '名称',
              cell: (item) => item.name,
              sortingField: 'name',
            },
            {
              id: 'description',
              header: '描述',
              cell: (item) => item.description || '-',
            },
            {
              id: 'status',
              header: '状态',
              cell: (item) => statusBadge(item.status),
            },
            {
              id: 's3_location',
              header: 'S3位置',
              cell: (item) => (
                <Box fontSize="body-s" color="text-body-secondary">
                  s3://{item.s3_bucket}/{item.s3_prefix}
                </Box>
              ),
            },
            {
              id: 'opensearch_index',
              header: 'OpenSearch索引',
              cell: (item) => (
                <Box fontSize="body-s" color="text-body-secondary">
                  {item.opensearch_index_name || '-'}
                </Box>
              ),
            },
            {
              id: 'created_at',
              header: '创建时间',
              cell: (item) => new Date(item.created_at).toLocaleString('zh-CN'),
              sortingField: 'created_at',
            },
            {
              id: 'actions',
              header: '操作',
              cell: (item) => (
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    variant="inline-link"
                    onClick={() => router.push(`/documents?kb_id=${item.id}`)}
                  >
                    查看文档
                  </Button>
                  <Button
                    variant="inline-link"
                    onClick={() => router.push(`/query?kb_id=${item.id}`)}
                  >
                    开始提问
                  </Button>
                </SpaceBetween>
              ),
            },
          ]}
          items={filteredKnowledgeBases}
          selectionType="multi"
          trackBy="id"
          empty={
            <Box textAlign="center" color="inherit">
              <b>暂无知识库</b>
              <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                点击"创建知识库"按钮开始使用
              </Box>
            </Box>
          }
          filter={
            <TextFilter
              filteringText={filterText}
              onChange={({ detail }) => setFilterText(detail.filteringText)}
              filteringPlaceholder="搜索知识库"
            />
          }
          header={
            <Header
              counter={`(${filteredKnowledgeBases.length})`}
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    onClick={loadKnowledgeBases}
                    iconName="refresh"
                  >
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
              知识库
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

      {/* 创建知识库Modal */}
      <CreateKnowledgeBaseModal
        visible={createModalVisible}
        onDismiss={() => setCreateModalVisible(false)}
        onSuccess={() => {
          setCreateModalVisible(false);
          loadKnowledgeBases();
        }}
      />

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
          确定要删除选中的 {selectedItems.length} 个知识库吗？
          <br />
          <Box color="text-status-error" variant="p">
            警告：删除知识库将同时删除其中的所有文档、向量数据和查询历史，此操作不可恢复！
          </Box>
        </Box>
      </Modal>
    </SpaceBetween>
  );
}
