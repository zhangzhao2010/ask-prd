'use client';

import { useState, useEffect } from 'react';
import {
  Container,
  Header,
  Table,
  Button,
  SpaceBetween,
  Box,
  Alert,
  Modal,
  FormField,
  Input,
  Badge,
} from '@cloudscape-design/components';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { apiClient } from '@/services/api';
import { User } from '@/services/auth';

function UserManagementContent() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // 创建用户modal状态
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [creating, setCreating] = useState(false);

  // 删除确认modal状态
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [userToDelete, setUserToDelete] = useState<User | null>(null);
  const [deleting, setDeleting] = useState(false);

  // 加载用户列表
  const loadUsers = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await apiClient.listUsers();
      setUsers(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  // 创建用户
  const handleCreateUser = async () => {
    if (!newUsername || !newPassword) {
      setError('用户名和密码不能为空');
      return;
    }

    try {
      setCreating(true);
      setError('');
      await apiClient.createUser(newUsername, newPassword);
      setSuccess(`用户 ${newUsername} 创建成功`);
      setShowCreateModal(false);
      setNewUsername('');
      setNewPassword('');
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建用户失败');
    } finally {
      setCreating(false);
    }
  };

  // 删除用户
  const handleDeleteUser = async () => {
    if (!userToDelete) return;

    try {
      setDeleting(true);
      setError('');
      await apiClient.deleteUser(userToDelete.id);
      setSuccess(`用户 ${userToDelete.username} 已删除`);
      setShowDeleteModal(false);
      setUserToDelete(null);
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除用户失败');
    } finally {
      setDeleting(false);
    }
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
            description="管理系统用户"
            actions={
              <Button
                variant="primary"
                onClick={() => setShowCreateModal(true)}
              >
                创建用户
              </Button>
            }
          >
            用户管理
          </Header>
        }
      >
        <Table
          columnDefinitions={[
            {
              id: 'id',
              header: 'ID',
              cell: (item) => item.id,
              width: 60,
            },
            {
              id: 'username',
              header: '用户名',
              cell: (item) => item.username,
            },
            {
              id: 'role',
              header: '角色',
              cell: (item) => (
                <Badge color={item.role === 'admin' ? 'blue' : 'grey'}>
                  {item.role === 'admin' ? '管理员' : '普通用户'}
                </Badge>
              ),
            },
            {
              id: 'is_active',
              header: '状态',
              cell: (item) => (
                <Badge color={item.is_active ? 'green' : 'red'}>
                  {item.is_active ? '激活' : '禁用'}
                </Badge>
              ),
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
                <Button
                  disabled={item.role === 'admin'} // 不能删除管理员
                  onClick={() => {
                    setUserToDelete(item);
                    setShowDeleteModal(true);
                  }}
                >
                  删除
                </Button>
              ),
            },
          ]}
          items={users}
          loading={loading}
          loadingText="加载中..."
          empty={
            <Box textAlign="center" color="inherit">
              <b>没有用户</b>
              <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                系统中还没有任何用户
              </Box>
            </Box>
          }
        />
      </Container>

      {/* 创建用户Modal */}
      <Modal
        visible={showCreateModal}
        onDismiss={() => setShowCreateModal(false)}
        header="创建新用户"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="link"
                onClick={() => setShowCreateModal(false)}
              >
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleCreateUser}
                loading={creating}
              >
                创建
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween size="m">
          <FormField label="用户名" description="请输入用户名">
            <Input
              value={newUsername}
              onChange={({ detail }) => setNewUsername(detail.value)}
              placeholder="用户名"
            />
          </FormField>

          <FormField label="密码" description="请输入初始密码">
            <Input
              value={newPassword}
              onChange={({ detail }) => setNewPassword(detail.value)}
              placeholder="密码"
              type="password"
            />
          </FormField>

          <Alert type="info">
            新用户默认角色为"普通用户"，创建后无法修改为管理员。
          </Alert>
        </SpaceBetween>
      </Modal>

      {/* 删除确认Modal */}
      <Modal
        visible={showDeleteModal}
        onDismiss={() => setShowDeleteModal(false)}
        header="确认删除用户"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="link"
                onClick={() => setShowDeleteModal(false)}
              >
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleDeleteUser}
                loading={deleting}
              >
                确认删除
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween size="m">
          <Box>
            确定要删除用户 <strong>{userToDelete?.username}</strong> 吗？
          </Box>
          <Alert type="warning">
            删除用户会同时删除：
            <ul>
              <li>该用户拥有的所有知识库</li>
              <li>所有相关文档和chunks</li>
              <li>该用户的所有权限</li>
              <li>该用户的查询历史</li>
            </ul>
            此操作不可撤销！
          </Alert>
        </SpaceBetween>
      </Modal>
    </SpaceBetween>
  );
}

export default function UserManagementPage() {
  return (
    <ProtectedRoute requireAdmin={true}>
      <UserManagementContent />
    </ProtectedRoute>
  );
}
