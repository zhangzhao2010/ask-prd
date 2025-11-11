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
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // 表单验证
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = '请输入知识库名称';
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

        {errors.submit && (
          <Box color="text-status-error">{errors.submit}</Box>
        )}
      </SpaceBetween>
    </Modal>
  );
}
