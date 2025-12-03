'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import {
  Container,
  Header,
  FormField,
  Input,
  Button,
  SpaceBetween,
  Alert,
  Box,
} from '@cloudscape-design/components';
import { authService } from '@/services/auth';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.login(username, password);
      // 登录成功，跳转到首页
      router.push('/knowledge-bases');
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box padding={{ vertical: 'xxxl' }}>
      <Container
        header={
          <Header variant="h1" description="请使用您的账号登录">
            ASK-PRD 系统登录
          </Header>
        }
      >
        <form onSubmit={handleSubmit}>
          <SpaceBetween size="l">
            {error && (
              <Alert type="error" dismissible onDismiss={() => setError('')}>
                {error}
              </Alert>
            )}

            <FormField label="用户名" description="请输入您的用户名">
              <Input
                value={username}
                onChange={({ detail }) => setUsername(detail.value)}
                placeholder="用户名"
                disabled={loading}
                autoComplete="username"
              />
            </FormField>

            <FormField label="密码" description="请输入您的密码">
              <Input
                value={password}
                onChange={({ detail }) => setPassword(detail.value)}
                placeholder="密码"
                type="password"
                disabled={loading}
                autoComplete="current-password"
              />
            </FormField>

            <Button
              variant="primary"
              loading={loading}
              formAction="submit"
              fullWidth
            >
              登录
            </Button>

            <Alert type="info">
              <Box variant="small">
                <strong>默认管理员账号：</strong>
                <br />
                用户名：admin
                <br />
                密码：admin123
                <br />
                <br />
                ⚠️ 首次登录后请立即修改密码
              </Box>
            </Alert>
          </SpaceBetween>
        </form>
      </Container>
    </Box>
  );
}
