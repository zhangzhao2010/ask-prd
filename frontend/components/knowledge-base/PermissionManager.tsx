'use client';

import { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Select,
  Table,
  Button,
  Box,
  Alert,
  Modal,
  Input,
  Badge,
  ColumnLayout,
} from '@cloudscape-design/components';
import { apiClient } from '@/services/api';

interface Permission {
  id: number;
  kb_id: string;
  user_id: number;
  username: string;
  permission_type: 'read' | 'write';
  granted_by: number;
  created_at: string;
}

interface PermissionManagerProps {
  kbId: string;
  kbName: string;
  currentVisibility: 'private' | 'public' | 'shared';
  isOwner: boolean;
  onUpdate?: () => void;
}

export function PermissionManager({
  kbId,
  kbName,
  currentVisibility,
  isOwner,
  onUpdate,
}: PermissionManagerProps) {
  const [visibility, setVisibility] = useState(currentVisibility);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // 添加权限modal状态
  const [showAddModal, setShowAddModal] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPermType, setNewPermType] = useState<'read' | 'write'>('read');
  const [adding, setAdding] = useState(false);

  // 删除权限modal状态
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [permToDelete, setPermToDelete] = useState<Permission | null>(null);
  const [deleting, setDeleting] = useState(false);

  // 加载权限列表
  const loadPermissions = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await apiClient.listKBPermissions(kbId);
      setPermissions(data.permissions);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载权限列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setVisibility(currentVisibility);
    loadPermissions();
  }, [kbId, currentVisibility]);

  // 更新可见性
  const handleVisibilityChange = async (newVisibility: 'private' | 'public' | 'shared') => {
    try {
      setError('');
      await apiClient.updateKBVisibility(kbId, newVisibility);
      setVisibility(newVisibility);
      setSuccess(`可见性已更新为: ${getVisibilityLabel(newVisibility)}`);
      onUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新可见性失败');
    }
  };

  // 添加权限
  const handleAddPermission = async () => {
    if (!newUsername) {
      setError('请输入用户名');
      return;
    }

    try {
      setAdding(true);
      setError('');
      await apiClient.grantKBPermission(kbId, newUsername, newPermType);
      setSuccess(`已授予 ${newUsername} ${newPermType === 'read' ? '只读' : '管理'}权限`);
      setShowAddModal(false);
      setNewUsername('');
      setNewPermType('read');
      loadPermissions();
    } catch (err) {
      setError(err instanceof Error ? err.message : '授予权限失败');
    } finally {
      setAdding(false);
    }
  };

  // 删除权限
  const handleDeletePermission = async () => {
    if (!permToDelete) return;

    try {
      setDeleting(true);
      setError('');
      await apiClient.revokeKBPermission(kbId, permToDelete.user_id);
      setSuccess(`已撤销 ${permToDelete.username} 的权限`);
      setShowDeleteModal(false);
      setPermToDelete(null);
      loadPermissions();
    } catch (err) {
      setError(err instanceof Error ? err.message : '撤销权限失败');
    } finally {
      setDeleting(false);
    }
  };

  const getVisibilityLabel = (vis: string) => {
    switch (vis) {
      case 'private':
        return '私有';
      case 'public':
        return '公开';
      case 'shared':
        return '共享';
      default:
        return vis;
    }
  };

  const getPermissionLabel = (perm: string) => {
    return perm === 'read' ? '只读' : '管理';
  };

  if (!isOwner) {
    return (
      <Container header={<Header variant="h2">权限管理</Header>}>
        <Alert type="info">只有知识库所有者可以管理权限</Alert>
      </Container>
    );
  }

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

      {/* 可见性设置 */}
      <Container
        header={
          <Header
            variant="h2"
            description="设置知识库的可见性级别"
          >
            可见性设置
          </Header>
        }
      >
        <SpaceBetween size="m">
          <FormField
            label="当前可见性"
            description="选择谁可以看到这个知识库"
          >
            <Select
              selectedOption={{
                label: getVisibilityLabel(visibility),
                value: visibility,
              }}
              onChange={({ detail }) =>
                handleVisibilityChange(detail.selectedOption.value as any)
              }
              options={[
                {
                  label: '私有 - 仅所有者可见',
                  value: 'private',
                  description: '只有您可以访问此知识库',
                },
                {
                  label: '公开 - 所有人可见',
                  value: 'public',
                  description: '所有登录用户都可以查看（默认只读）',
                },
                {
                  label: '共享 - 指定人可见',
                  value: 'shared',
                  description: '仅被授权的用户可以访问',
                },
              ]}
            />
          </FormField>

          <ColumnLayout columns={3} variant="text-grid">
            <div>
              <Box variant="awsui-key-label">私有</Box>
              <div>仅所有者可见，最安全</div>
            </div>
            <div>
              <Box variant="awsui-key-label">公开</Box>
              <div>所有人可读，需授权才可写</div>
            </div>
            <div>
              <Box variant="awsui-key-label">共享</Box>
              <div>通过权限表精确控制访问</div>
            </div>
          </ColumnLayout>
        </SpaceBetween>
      </Container>

      {/* 权限列表 */}
      <Container
        header={
          <Header
            variant="h2"
            description="管理用户访问权限"
            actions={
              <Button
                variant="primary"
                onClick={() => setShowAddModal(true)}
                disabled={visibility === 'private'}
              >
                添加权限
              </Button>
            }
          >
            用户权限列表
          </Header>
        }
      >
        {visibility === 'private' && (
          <Alert type="info">
            私有知识库不需要配置权限表，只有所有者可以访问。
            如需共享给其他用户，请先将可见性改为"公开"或"共享"。
          </Alert>
        )}

        <Table
          columnDefinitions={[
            {
              id: 'username',
              header: '用户名',
              cell: (item) => item.username,
            },
            {
              id: 'permission_type',
              header: '权限类型',
              cell: (item) => (
                <Badge color={item.permission_type === 'write' ? 'blue' : 'grey'}>
                  {getPermissionLabel(item.permission_type)}
                </Badge>
              ),
            },
            {
              id: 'created_at',
              header: '授予时间',
              cell: (item) => new Date(item.created_at).toLocaleString('zh-CN'),
            },
            {
              id: 'actions',
              header: '操作',
              cell: (item) => (
                <Button
                  onClick={() => {
                    setPermToDelete(item);
                    setShowDeleteModal(true);
                  }}
                >
                  撤销
                </Button>
              ),
            },
          ]}
          items={permissions}
          loading={loading}
          loadingText="加载中..."
          empty={
            <Box textAlign="center" color="inherit">
              <b>没有权限记录</b>
              <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                {visibility === 'public'
                  ? '公开知识库默认所有人可读，仅需授予写权限时添加'
                  : '还没有授予任何用户权限'}
              </Box>
            </Box>
          }
        />
      </Container>

      {/* 添加权限Modal */}
      <Modal
        visible={showAddModal}
        onDismiss={() => setShowAddModal(false)}
        header="添加用户权限"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={() => setShowAddModal(false)}>
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleAddPermission}
                loading={adding}
              >
                添加
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween size="m">
          <FormField label="用户名" description="输入要授权的用户名">
            <Input
              value={newUsername}
              onChange={({ detail }) => setNewUsername(detail.value)}
              placeholder="用户名"
            />
          </FormField>

          <FormField label="权限类型" description="选择授予的权限级别">
            <Select
              selectedOption={{
                label: getPermissionLabel(newPermType),
                value: newPermType,
              }}
              onChange={({ detail }) =>
                setNewPermType(detail.selectedOption.value as 'read' | 'write')
              }
              options={[
                {
                  label: '只读',
                  value: 'read',
                  description: '可以查看文档和问答',
                },
                {
                  label: '管理',
                  value: 'write',
                  description: '可以上传/删除文档，修改知识库',
                },
              ]}
            />
          </FormField>

          <Alert type="info">
            如果该用户已有权限，将会更新为新的权限类型。
          </Alert>
        </SpaceBetween>
      </Modal>

      {/* 删除权限Modal */}
      <Modal
        visible={showDeleteModal}
        onDismiss={() => setShowDeleteModal(false)}
        header="撤销用户权限"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={() => setShowDeleteModal(false)}>
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleDeletePermission}
                loading={deleting}
              >
                确认撤销
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween size="m">
          <Box>
            确定要撤销用户 <strong>{permToDelete?.username}</strong> 的权限吗？
          </Box>
          <Alert type="warning">
            撤销后，该用户将无法访问此知识库
            {visibility === 'shared' && '（共享知识库）'}
            {visibility === 'public' && '的写权限（仍可读取）'}。
          </Alert>
        </SpaceBetween>
      </Modal>
    </SpaceBetween>
  );
}
