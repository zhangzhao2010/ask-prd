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
  Badge,
  Modal,
  Alert,
} from '@cloudscape-design/components';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { PermissionManager } from '@/components/knowledge-base/PermissionManager';
import { authService } from '@/services/auth';
import CreateKnowledgeBaseModal from '@/components/knowledge-base/CreateKnowledgeBaseModal';

interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  status: string;
  opensearch_index_name?: string;
  visibility: 'private' | 'public' | 'shared';
  owner_id: number;
  created_at: string;
  updated_at: string;
}

function KnowledgeBasesContent() {
  const router = useRouter();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [selectedItems, setSelectedItems] = useState<KnowledgeBase[]>([]);

  // Modal状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [permModalVisible, setPermModalVisible] = useState(false);
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const currentUserId = authService.getUserId();
  const isAdmin = authService.isAdmin();

  // 加载知识库列表
  const loadKnowledgeBases = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/v1/knowledge-bases', {
        headers: {
          Authorization: `Bearer ${authService.getToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error('加载失败');
      }

      const data = await response.json();
      setKnowledgeBases(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载知识库列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  // 删除知识库
  const handleDelete = async () => {
    if (selectedItems.length === 0) return;

    setDeleteLoading(true);
    try {
      await Promise.all(
        selectedItems.map((item) =>
          fetch(`/api/v1/knowledge-bases/${item.id}`, {
            method: 'DELETE',
            headers: {
              Authorization: `Bearer ${authService.getToken()}`,
            },
          })
        )
      );
      setSuccess(`已删除 ${selectedItems.length} 个知识库`);
      setDeleteModalVisible(false);
      setSelectedItems([]);
      loadKnowledgeBases();
    } catch (err) {
      setError('删除失败');
    } finally {
      setDeleteLoading(false);
    }
  };

  // 打开权限管理
  const handleManagePermissions = (kb: KnowledgeBase) => {
    setSelectedKB(kb);
    setPermModalVisible(true);
  };

  // 可见性Badge
  const visibilityBadge = (visibility: string, ownerId: number) => {
    const isOwner = ownerId === currentUserId;
    const map: Record<string, { text: string; color: any }> = {
      private: { text: '私有', color: 'red' },
      public: { text: '公开', color: 'green' },
      shared: { text: '共享', color: 'blue' },
    };
    const config = map[visibility] || { text: visibility, color: 'grey' };
    return (
      <SpaceBetween direction="horizontal" size="xs">
        <Badge color={config.color}>{config.text}</Badge>
        {isOwner && <Badge>所有者</Badge>}
        {isAdmin && !isOwner && <Badge color="blue">管理员</Badge>}
      </SpaceBetween>
    );
  };

  // 状态Badge
  const statusBadge = (status: string) => {
    const map: Record<string, { text: string; color: any }> = {
      active: { text: '已激活', color: 'green' },
      creating: { text: '创建中', color: 'blue' },
      failed: { text: '失败', color: 'red' },
    };
    const config = map[status] || { text: status, color: 'grey' };
    return <Badge color={config.color}>{config.text}</Badge>;
  };

  // 检查是否可以删除
  const canDelete = (kb: KnowledgeBase) => {
    return kb.owner_id === currentUserId || isAdmin;
  };

  // 检查是否可以管理权限
  const canManagePermissions = (kb: KnowledgeBase) => {
    return kb.owner_id === currentUserId || isAdmin;
  };

  return (
    <SpaceBetween size="l">
      {error && (
        <Alert type="error" dismissible onDismiss={() => setError('')}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert type="success" dismissible onDismiss={() => setSuccess('')}>
          {success}
        </Alert>
      )}

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
          loading={loading}
          selectedItems={selectedItems}
          onSelectionChange={({ detail }) => setSelectedItems(detail.selectedItems)}
          columnDefinitions={[
            {
              id: 'name',
              header: '名称',
              cell: (item) => item.name,
            },
            {
              id: 'description',
              header: '描述',
              cell: (item) => item.description || '-',
            },
            {
              id: 'visibility',
              header: '可见性',
              cell: (item) => visibilityBadge(item.visibility, item.owner_id),
            },
            {
              id: 'status',
              header: '状态',
              cell: (item) => statusBadge(item.status),
            },
            {
              id: 'created_at',
              header: '创建时间',
              cell: (item) => new Date(item.created_at).toLocaleString('zh-CN'),
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
                    文档
                  </Button>
                  <Button
                    variant="inline-link"
                    onClick={() => router.push(`/query?kb_id=${item.id}`)}
                  >
                    问答
                  </Button>
                  {canManagePermissions(item) && (
                    <Button
                      variant="inline-link"
                      onClick={() => handleManagePermissions(item)}
                    >
                      权限
                    </Button>
                  )}
                </SpaceBetween>
              ),
            },
          ]}
          items={knowledgeBases}
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
          header={
            <Header
              counter={`(${knowledgeBases.length})`}
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={loadKnowledgeBases} iconName="refresh">
                    刷新
                  </Button>
                  <Button
                    onClick={() => setDeleteModalVisible(true)}
                    disabled={
                      selectedItems.length === 0 ||
                      !selectedItems.every(canDelete)
                    }
                  >
                    删除
                  </Button>
                </SpaceBetween>
              }
            >
              知识库
            </Header>
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
              <Button
                variant="link"
                onClick={() => setDeleteModalVisible(false)}
              >
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleDelete}
                loading={deleteLoading}
              >
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

      {/* 权限管理Modal */}
      <Modal
        visible={permModalVisible}
        onDismiss={() => setPermModalVisible(false)}
        header={`权限管理 - ${selectedKB?.name}`}
        size="large"
      >
        {selectedKB && (
          <PermissionManager
            kbId={selectedKB.id}
            kbName={selectedKB.name}
            currentVisibility={selectedKB.visibility}
            isOwner={canManagePermissions(selectedKB)}
            onUpdate={loadKnowledgeBases}
          />
        )}
      </Modal>
    </SpaceBetween>
  );
}

export default function KnowledgeBasesPage() {
  return (
    <ProtectedRoute>
      <KnowledgeBasesContent />
    </ProtectedRoute>
  );
}
