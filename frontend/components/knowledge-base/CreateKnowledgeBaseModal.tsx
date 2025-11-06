'use client';

import { useState } from 'react';
import {
  Modal,
  Box,
  SpaceBetween,
  FormField,
  Input,
  Textarea,
  Button,
} from '@cloudscape-design/components';
import { knowledgeBaseAPI } from '@/services/api';
import type { KnowledgeBaseCreate } from '@/types';

interface CreateKnowledgeBaseModalProps {
  visible: boolean;
  onDismiss: () => void;
  onSuccess: () => void;
}

export default function CreateKnowledgeBaseModal({
  visible,
  onDismiss,
  onSuccess,
}: CreateKnowledgeBaseModalProps) {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<KnowledgeBaseCreate>({
    name: '',
    description: '',
    s3_bucket: '',
    s3_prefix: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // 表单验证
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = '请输入知识库名称';
    }

    if (!formData.s3_bucket.trim()) {
      newErrors.s3_bucket = '请输入S3桶名';
    }

    if (!formData.s3_prefix.trim()) {
      newErrors.s3_prefix = '请输入S3路径前缀';
    } else if (!formData.s3_prefix.endsWith('/')) {
      newErrors.s3_prefix = 'S3路径前缀必须以 / 结尾';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 提交表单
  const handleSubmit = async () => {
    if (!validate()) {
      return;
    }

    setLoading(true);
    try {
      await knowledgeBaseAPI.create(formData);
      onSuccess();
      // 重置表单
      setFormData({
        name: '',
        description: '',
        s3_bucket: '',
        s3_prefix: '',
      });
      setErrors({});
    } catch (error: any) {
      setErrors({
        submit: error.message || '创建失败',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      visible={visible}
      onDismiss={onDismiss}
      header="创建知识库"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss}>
              取消
            </Button>
            <Button variant="primary" onClick={handleSubmit} loading={loading}>
              创建
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="m">
        <FormField
          label="知识库名称"
          errorText={errors.name}
          description="为知识库起一个有意义的名称"
        >
          <Input
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.detail.value })}
            placeholder="例如：产品PRD知识库"
          />
        </FormField>

        <FormField
          label="描述信息"
          description="选填，描述知识库的用途"
        >
          <Textarea
            value={formData.description || ''}
            onChange={(e) => setFormData({ ...formData, description: e.detail.value })}
            placeholder="例如：包含产品迭代的所有PRD文档"
            rows={3}
          />
        </FormField>

        <FormField
          label="S3桶名"
          errorText={errors.s3_bucket}
          description="存储文档的S3桶"
        >
          <Input
            value={formData.s3_bucket}
            onChange={(e) => setFormData({ ...formData, s3_bucket: e.detail.value })}
            placeholder="例如：my-prd-bucket"
          />
        </FormField>

        <FormField
          label="S3路径前缀"
          errorText={errors.s3_prefix}
          description="S3路径前缀，必须以 / 结尾"
        >
          <Input
            value={formData.s3_prefix}
            onChange={(e) => setFormData({ ...formData, s3_prefix: e.detail.value })}
            placeholder="例如：prds/product-a/"
          />
        </FormField>

        {errors.submit && (
          <Box color="text-status-error">{errors.submit}</Box>
        )}
      </SpaceBetween>
    </Modal>
  );
}
