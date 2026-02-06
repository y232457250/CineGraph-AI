// frontend-ui/src/types/canvas.ts
/**
 * 无限画布类型定义
 */

// ==================== 基础类型 ====================

export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

// ==================== 项目类型 ====================

export interface CanvasProject {
  id: string;
  name: string;
  description?: string;
  theme?: string;
  style?: 'absurd' | 'emotional' | 'suspense';
  viewport?: {
    x: number;
    y: number;
    zoom: number;
  };
  nodes?: CanvasNode[];
  edges?: CanvasEdge[];
  sequences?: Sequence[];
  created_at?: string;
  updated_at?: string;
}

// ==================== 节点类型 ====================

export type NodeType = 'root' | 'scene' | 'clip' | 'transition' | 'effect' | 'note';

export interface CanvasNode {
  id: string;
  project_id: string;
  parent_id?: string;
  line_id?: number;
  node_type: NodeType;
  title: string;
  content?: string;
  order: number;
  depth: number;
  position: Position;
  size: Size;
  z_index: number;
  color?: string;
  trim_start?: number;
  trim_end?: number;
  volume?: number;
  collapsed: boolean;
  locked: boolean;
  // 关联的台词信息
  line?: LineData;
}

// ==================== 连线类型 ====================

export type AnchorType = 'input' | 'output' | 'contrast' | 'context';
export type RelationType = 'continuation' | 'contrast' | 'escalation' | 'callback';

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  source_anchor: AnchorType;
  target_anchor: AnchorType;
  relation_type?: RelationType;
  strength: number;
  color?: string;
  width: number;
  is_dashed: boolean;
  is_animated: boolean;
  label?: string;
}

// ==================== 时间轴类型 ====================

export interface Sequence {
  id: number;
  project_id: string;
  name: string;
  total_duration: number;
  target_duration: number;
  items: SequenceItem[];
}

export interface SequenceItem {
  id: number;
  sequence_id: number;
  node_id: string;
  order: number;
  trim_start: number;
  trim_end?: number;
  volume: number;
  transition_type: 'cut' | 'fade' | 'jitter';
  transition_duration: number;
}

// ==================== 台词数据类型 ====================

export interface MashupTags {
  sentence_type?: string;
  emotion?: string;
  tone?: string;
  character_type?: string;
  can_follow?: string[];
  can_lead_to?: string[];
  keywords?: string[];
  primary_function?: string;
  style_effect?: string;
}

export interface LineData {
  id: string;
  text: string;
  vector_text?: string;
  movie_id: string;
  movie?: string;
  episode_number?: number;
  character?: string;
  source?: {
    media_id: string;
    start: number;
    end: number;
  };
  mashup_tags?: MashupTags;
  intensity?: number;
  hook_score?: number;
  ambiguity?: number;
  duration?: number;
  editing_params?: {
    rhythm?: string;
    duration?: number;
  };
  semantic_summary?: string;
  vectorized?: boolean;
}

// ==================== API 响应类型 ====================

export interface ProjectListResponse {
  success: boolean;
  projects: CanvasProject[];
}

export interface ProjectResponse {
  success: boolean;
  project: CanvasProject;
}

export interface NodeResponse {
  success: boolean;
  node: CanvasNode;
}

export interface EdgeResponse {
  success: boolean;
  edge: CanvasEdge;
}

export interface LinesSearchResponse {
  success: boolean;
  lines: LineData[];
  count: number;
}

export interface ConnectionRule {
  from: string;
  to: string;
  weight: number;
  transition_type?: string;
}

export interface RulesResponse {
  success: boolean;
  rules: ConnectionRule[];
}

// ==================== 请求类型 ====================

export interface CreateProjectRequest {
  name: string;
  description?: string;
  theme?: string;
  style?: string;
}

export interface CreateNodeRequest {
  parent_id?: string;
  line_id?: number;
  node_type?: NodeType;
  title?: string;
  content?: string;
  position?: Position;
  size?: Size;
  color?: string;
  order?: number;
}

export interface UpdateNodeRequest {
  title?: string;
  content?: string;
  position?: Position;
  size?: Size;
  color?: string;
  collapsed?: boolean;
  locked?: boolean;
  volume?: number;
  trim_start?: number;
  trim_end?: number;
}

export interface CreateEdgeRequest {
  source: string;
  target: string;
  source_anchor?: AnchorType;
  target_anchor?: AnchorType;
  relation_type?: RelationType;
  strength?: number;
  color?: string;
  label?: string;
}

export interface SearchLinesParams {
  sentence_type?: string;
  emotion?: string;
  tone?: string;
  character_type?: string;
  min_intensity?: number;
  max_duration?: number;
  keyword?: string;
  limit?: number;
}
