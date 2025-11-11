'use client';

import Link from 'next/link';
import {
  Container,
  Header,
  Box,
  SpaceBetween,
  Button,
} from '@cloudscape-design/components';

export default function ForbiddenPage() {
  return (
    <Box padding={{ vertical: 'xxxl' }}>
      <Container
        header={
          <Header
            variant="h1"
            description="您没有权限访问此页面"
          >
            403 - 禁止访问
          </Header>
        }
      >
        <SpaceBetween size="l">
          <Box variant="p">
            抱歉，您没有足够的权限访问此页面。
            <br />
            如果您认为这是一个错误，请联系管理员。
          </Box>

          <Box>
            <SpaceBetween direction="horizontal" size="xs">
              <Link href="/knowledge-bases">
                <Button>返回首页</Button>
              </Link>
              <Link href="/login">
                <Button variant="primary">重新登录</Button>
              </Link>
            </SpaceBetween>
          </Box>
        </SpaceBetween>
      </Container>
    </Box>
  );
}
