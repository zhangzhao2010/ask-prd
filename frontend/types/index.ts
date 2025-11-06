/**
 * TypeScript类型定义
 * 对应后端Schema: backend/app/models/schemas.py
 */

// ============ 基础响应模型 ============

export interface ErrorResponse {
  error_code: string;
  message: string;
  details?: Record<string, any>;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

// ============ 知识库相关模型 ============

export interface KnowledgeBaseCreate {
  name: string;
  description?: string;
  s3_bucket: string;
  s3_prefix: string;
}

export interface KnowledgeBaseUpdate {
  name?: string;
  description?: string;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  s3_bucket: string;
  s3_prefix: string;
  opensearch_collection_id?: string;
  opensearch_index_name?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeBaseStats {
  document_count: number;
  chunk_count: number;
  total_size_bytes: number;
}

export interface KnowledgeBaseDetail extends KnowledgeBase {
  stats: KnowledgeBaseStats;
}

export interface KnowledgeBaseListResponse {
  items: KnowledgeBase[];
  meta: PaginationMeta;
}

// ============ 文档相关模型 ============

export interface Document {
  id: string;
  kb_id: string;
  filename: string;
  s3_key: string;
  s3_key_markdown?: string;
  file_size?: number;
  page_count?: number;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends Document {
  stats: Record<string, number>;
}

export interface DocumentListResponse {
  items: Document[];
  meta: PaginationMeta;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  s3_key: string;
  file_size: number;
  message: string;
}

// ============ Chunk相关模型 ============

export interface Chunk {
  id: string;
  document_id: string;
  kb_id: string;
  chunk_type: 'text' | 'image';
  chunk_index: number;
  content?: string;  // 文本chunk
  image_filename?: string;  // 图片chunk
  image_description?: string;  // 图片描述
  image_type?: string;  // 图片类型
  token_count?: number;
  created_at: string;
}

// ============ 同步任务相关模型 ============

export interface SyncTaskCreate {
  kb_id: string;
  task_type: 'full_sync' | 'incremental' | 'delete';
  document_ids?: string[];
}

export interface SyncTask {
  id: string;
  kb_id: string;
  task_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'partial_success';
  progress: number;  // 0-100
  current_step?: string;
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface SyncTaskListResponse {
  items: SyncTask[];
  meta: PaginationMeta;
}

// ============ 查询相关模型 ============

export interface QueryRequest {
  kb_id: string;
  query_text: string;
}

export interface CitationItem {
  chunk_id: string;
  chunk_type: 'text' | 'image';
  document_id: string;
  document_name: string;
  content?: string;  // 文本内容或图片描述
  chunk_index: number;
  image_url?: string;  // 图片URL（如果是图片chunk）
}

export interface QueryResponse {
  query_id: string;
  query_text: string;
  answer: string;
  citations: CitationItem[];
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  response_time_ms: number;
}

export interface QueryHistory {
  id: string;
  kb_id: string;
  query_text: string;
  answer?: string;
  total_tokens?: number;
  response_time_ms?: number;
  status: 'completed' | 'failed';
  created_at: string;
}

export interface QueryHistoryListResponse {
  items: QueryHistory[];
  meta: PaginationMeta;
}

// ============ 流式输出事件模型 ============

export interface StreamEvent {
  type: string;
  timestamp: string;
}

export interface StatusEvent extends StreamEvent {
  type: 'status';
  message: string;
}

export interface TextDeltaEvent extends StreamEvent {
  type: 'text_delta';
  text: string;
}

export interface CompleteEvent extends StreamEvent {
  type: 'complete';
  citations: CitationItem[];
  metrics: Record<string, number>;
}

export interface ErrorEvent extends StreamEvent {
  type: 'error';
  error_code: string;
  message: string;
  details?: Record<string, any>;
}

export type QueryStreamEvent = StatusEvent | TextDeltaEvent | CompleteEvent | ErrorEvent;
