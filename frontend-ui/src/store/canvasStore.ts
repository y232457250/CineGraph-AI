// frontend-ui/src/store/canvasStore.ts
/**
 * 无限画布状态管理
 * 使用 zustand 管理画布状态
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  CanvasProject,
  CanvasNode,
  CanvasEdge,
  LineData,
  Position,
  Size,
  CreateProjectRequest,
  CreateNodeRequest,
  UpdateNodeRequest,
  CreateEdgeRequest,
  SearchLinesParams,
  ConnectionRule,
  Sequence,
} from '../types/canvas';

const API_BASE = 'http://127.0.0.1:8000';

// ==================== Store 类型 ====================

interface CanvasStore {
  // 状态
  projects: CanvasProject[];
  currentProject: CanvasProject | null;
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  sequences: Sequence[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  
  // 搜索结果
  searchResults: LineData[];
  connectionRules: ConnectionRule[];
  suggestedNextLines: LineData[];
  
  // 视口状态
  viewport: { x: number; y: number; zoom: number };
  
  // UI 状态
  isLoading: boolean;
  error: string | null;
  
  // ==================== 项目操作 ====================
  
  loadProjects: () => Promise<void>;
  createProject: (data: CreateProjectRequest) => Promise<CanvasProject | null>;
  loadProject: (projectId: string) => Promise<void>;
  updateProject: (projectId: string, data: Partial<CanvasProject>) => Promise<void>;
  deleteProject: (projectId: string) => Promise<void>;
  
  // ==================== 节点操作 ====================
  
  addNode: (data: CreateNodeRequest) => Promise<CanvasNode | null>;
  updateNode: (nodeId: string, data: UpdateNodeRequest) => Promise<void>;
  deleteNode: (nodeId: string) => Promise<void>;
  selectNode: (nodeId: string | null) => void;
  batchUpdateNodes: (nodes: Array<{ id: string; position?: Position; size?: Size }>) => Promise<void>;
  
  // ==================== 连线操作 ====================
  
  addEdge: (data: CreateEdgeRequest) => Promise<CanvasEdge | null>;
  deleteEdge: (edgeId: string) => Promise<void>;
  selectEdge: (edgeId: string | null) => void;
  
  // ==================== 视口操作 ====================
  
  setViewport: (viewport: { x: number; y: number; zoom: number }) => void;
  saveViewport: () => Promise<void>;
  
  // ==================== 台词搜索 ====================
  
  searchLines: (params: SearchLinesParams) => Promise<void>;
  getHookLines: (limit?: number) => Promise<void>;
  getNextLines: (lineId: string) => Promise<void>;
  loadConnectionRules: (fromType?: string) => Promise<void>;
  
  // ==================== 从搜索结果添加节点 ====================
  
  addLineToCanvas: (line: LineData, position: Position) => Promise<CanvasNode | null>;
  
  // ==================== 工具方法 ====================
  
  clearError: () => void;
  reset: () => void;
}

// ==================== Store 实现 ====================

export const useCanvasStore = create<CanvasStore>()(
  persist(
    (set, get) => ({
      // 初始状态
      projects: [],
      currentProject: null,
      nodes: [],
      edges: [],
      sequences: [],
      selectedNodeId: null,
      selectedEdgeId: null,
      searchResults: [],
      connectionRules: [],
      suggestedNextLines: [],
      viewport: { x: 0, y: 0, zoom: 1 },
      isLoading: false,
      error: null,
      
      // ==================== 项目操作 ====================
      
      loadProjects: async () => {
        set({ isLoading: true, error: null });
        try {
          const res = await fetch(`${API_BASE}/api/canvas/projects`);
          const data = await res.json();
          if (data.success) {
            set({ projects: data.projects });
          } else {
            throw new Error(data.detail || '加载项目失败');
          }
        } catch (e: any) {
          set({ error: e.message });
        } finally {
          set({ isLoading: false });
        }
      },
      
      createProject: async (reqData: CreateProjectRequest) => {
        set({ isLoading: true, error: null });
        try {
          const res = await fetch(`${API_BASE}/api/canvas/projects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reqData),
          });
          const data = await res.json();
          if (data.success) {
            set((state) => ({ projects: [data.project, ...state.projects] }));
            return data.project;
          } else {
            throw new Error(data.detail || '创建项目失败');
          }
        } catch (e: any) {
          set({ error: e.message });
          return null;
        } finally {
          set({ isLoading: false });
        }
      },
      
      loadProject: async (projectId: string) => {
        set({ isLoading: true, error: null });
        try {
          const res = await fetch(`${API_BASE}/api/canvas/projects/${projectId}?include_nodes=true`);
          const data = await res.json();
          if (data.success) {
            const project = data.project;
            set({
              currentProject: project,
              nodes: project.nodes || [],
              edges: project.edges || [],
              sequences: project.sequences || [],
              viewport: project.viewport || { x: 0, y: 0, zoom: 1 },
            });
          } else {
            throw new Error(data.detail || '加载项目失败');
          }
        } catch (e: any) {
          set({ error: e.message });
        } finally {
          set({ isLoading: false });
        }
      },
      
      updateProject: async (projectId: string, updates: Partial<CanvasProject>) => {
        try {
          const res = await fetch(`${API_BASE}/api/canvas/projects/${projectId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
          });
          const data = await res.json();
          if (!data.success) {
            throw new Error(data.detail || '更新项目失败');
          }
          // 更新本地状态
          set((state) => ({
            currentProject: state.currentProject?.id === projectId
              ? { ...state.currentProject, ...updates }
              : state.currentProject,
            projects: state.projects.map((p) =>
              p.id === projectId ? { ...p, ...updates } : p
            ),
          }));
        } catch (e: any) {
          set({ error: e.message });
        }
      },
      
      deleteProject: async (projectId: string) => {
        try {
          const res = await fetch(`${API_BASE}/api/canvas/projects/${projectId}`, {
            method: 'DELETE',
          });
          const data = await res.json();
          if (data.success) {
            set((state) => ({
              projects: state.projects.filter((p) => p.id !== projectId),
              currentProject: state.currentProject?.id === projectId ? null : state.currentProject,
            }));
          } else {
            throw new Error(data.detail || '删除项目失败');
          }
        } catch (e: any) {
          set({ error: e.message });
        }
      },
      
      // ==================== 节点操作 ====================
      
      addNode: async (nodeData: CreateNodeRequest) => {
        const { currentProject } = get();
        if (!currentProject) {
          set({ error: '请先选择或创建项目' });
          return null;
        }
        
        try {
          const res = await fetch(`${API_BASE}/api/canvas/projects/${currentProject.id}/nodes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(nodeData),
          });
          const data = await res.json();
          if (data.success) {
            set((state) => ({ nodes: [...state.nodes, data.node] }));
            return data.node;
          } else {
            throw new Error(data.detail || '添加节点失败');
          }
        } catch (e: any) {
          set({ error: e.message });
          return null;
        }
      },
      
      updateNode: async (nodeId: string, updates: UpdateNodeRequest) => {
        try {
          const res = await fetch(`${API_BASE}/api/canvas/nodes/${nodeId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
          });
          const data = await res.json();
          if (data.success) {
            set((state) => ({
              nodes: state.nodes.map((n) =>
                n.id === nodeId ? { ...n, ...updates } : n
              ),
            }));
          } else {
            throw new Error(data.detail || '更新节点失败');
          }
        } catch (e: any) {
          set({ error: e.message });
        }
      },
      
      deleteNode: async (nodeId: string) => {
        try {
          const res = await fetch(`${API_BASE}/api/canvas/nodes/${nodeId}`, {
            method: 'DELETE',
          });
          const data = await res.json();
          if (data.success) {
            set((state) => ({
              nodes: state.nodes.filter((n) => n.id !== nodeId),
              edges: state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
              selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
            }));
          } else {
            throw new Error(data.detail || '删除节点失败');
          }
        } catch (e: any) {
          set({ error: e.message });
        }
      },
      
      selectNode: (nodeId: string | null) => {
        set({ selectedNodeId: nodeId, selectedEdgeId: null });
      },
      
      batchUpdateNodes: async (nodes) => {
        const { currentProject } = get();
        if (!currentProject) return;
        
        try {
          const res = await fetch(`${API_BASE}/api/canvas/projects/${currentProject.id}/nodes/batch`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nodes }),
          });
          const data = await res.json();
          if (data.success) {
            // 更新本地状态
            set((state) => ({
              nodes: state.nodes.map((n) => {
                const update = nodes.find((u) => u.id === n.id);
                if (update) {
                  return {
                    ...n,
                    position: update.position || n.position,
                    size: update.size || n.size,
                  };
                }
                return n;
              }),
            }));
          }
        } catch (e: any) {
          console.error('批量更新节点失败:', e);
        }
      },
      
      // ==================== 连线操作 ====================
      
      addEdge: async (edgeData: CreateEdgeRequest) => {
        const { currentProject } = get();
        if (!currentProject) {
          set({ error: '请先选择或创建项目' });
          return null;
        }
        
        try {
          const res = await fetch(`${API_BASE}/api/canvas/projects/${currentProject.id}/edges`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(edgeData),
          });
          const data = await res.json();
          if (data.success) {
            set((state) => ({ edges: [...state.edges, data.edge] }));
            return data.edge;
          } else {
            throw new Error(data.detail || '添加连线失败');
          }
        } catch (e: any) {
          set({ error: e.message });
          return null;
        }
      },
      
      deleteEdge: async (edgeId: string) => {
        try {
          const res = await fetch(`${API_BASE}/api/canvas/edges/${edgeId}`, {
            method: 'DELETE',
          });
          const data = await res.json();
          if (data.success) {
            set((state) => ({
              edges: state.edges.filter((e) => e.id !== edgeId),
              selectedEdgeId: state.selectedEdgeId === edgeId ? null : state.selectedEdgeId,
            }));
          } else {
            throw new Error(data.detail || '删除连线失败');
          }
        } catch (e: any) {
          set({ error: e.message });
        }
      },
      
      selectEdge: (edgeId: string | null) => {
        set({ selectedEdgeId: edgeId, selectedNodeId: null });
      },
      
      // ==================== 视口操作 ====================
      
      setViewport: (viewport) => {
        set({ viewport });
      },
      
      saveViewport: async () => {
        const { currentProject, viewport } = get();
        if (!currentProject) return;
        
        await get().updateProject(currentProject.id, {
          viewport: {
            x: viewport.x,
            y: viewport.y,
            zoom: viewport.zoom,
          },
        } as any);
      },
      
      // ==================== 台词搜索 ====================
      
      searchLines: async (params: SearchLinesParams) => {
        try {
          const queryParams = new URLSearchParams();
          if (params.sentence_type) queryParams.append('sentence_type', params.sentence_type);
          if (params.emotion) queryParams.append('emotion', params.emotion);
          if (params.tone) queryParams.append('tone', params.tone);
          if (params.character_type) queryParams.append('character_type', params.character_type);
          if (params.min_intensity) queryParams.append('min_intensity', String(params.min_intensity));
          if (params.max_duration) queryParams.append('max_duration', String(params.max_duration));
          if (params.keyword) queryParams.append('keyword', params.keyword);
          if (params.limit) queryParams.append('limit', String(params.limit));
          
          const res = await fetch(`${API_BASE}/api/canvas/lines/search?${queryParams}`);
          const data = await res.json();
          if (data.success) {
            set({ searchResults: data.lines });
          }
        } catch (e: any) {
          console.error('搜索台词失败:', e);
        }
      },
      
      getHookLines: async (limit = 10) => {
        try {
          const res = await fetch(`${API_BASE}/api/canvas/lines/hooks?limit=${limit}`);
          const data = await res.json();
          if (data.success) {
            set({ searchResults: data.lines });
          }
        } catch (e: any) {
          console.error('获取钩子台词失败:', e);
        }
      },
      
      getNextLines: async (lineId: string) => {
        try {
          const res = await fetch(`${API_BASE}/api/canvas/lines/${lineId}/next`);
          const data = await res.json();
          if (data.success) {
            set({ suggestedNextLines: data.lines });
          }
        } catch (e: any) {
          console.error('获取下一句建议失败:', e);
        }
      },
      
      loadConnectionRules: async (fromType?: string) => {
        try {
          const url = fromType
            ? `${API_BASE}/api/canvas/rules?from_type=${fromType}`
            : `${API_BASE}/api/canvas/rules`;
          const res = await fetch(url);
          const data = await res.json();
          if (data.success) {
            set({ connectionRules: data.rules });
          }
        } catch (e: any) {
          console.error('加载接话规则失败:', e);
        }
      },
      
      // ==================== 从搜索结果添加节点 ====================
      
      addLineToCanvas: async (line: LineData, position: Position) => {
        const nodeData: CreateNodeRequest = {
          line_id: parseInt(line.id) || undefined,
          node_type: 'clip',
          title: line.text.substring(0, 30) + (line.text.length > 30 ? '...' : ''),
          content: line.semantic_summary || line.text,
          position,
          size: { width: 200, height: 80 },
          color: getColorByEmotion(line.mashup_tags?.emotion),
        };
        
        return get().addNode(nodeData);
      },
      
      // ==================== 工具方法 ====================
      
      clearError: () => set({ error: null }),
      
      reset: () => set({
        currentProject: null,
        nodes: [],
        edges: [],
        sequences: [],
        selectedNodeId: null,
        selectedEdgeId: null,
        searchResults: [],
        suggestedNextLines: [],
        viewport: { x: 0, y: 0, zoom: 1 },
      }),
    }),
    {
      name: 'cinegraph-canvas',
      partialize: (state) => ({
        // 只持久化项目列表和当前项目ID
        projects: state.projects.map((p) => ({ id: p.id, name: p.name })),
      }),
    }
  )
);

// ==================== 辅助函数 ====================

function getColorByEmotion(emotion?: string): string {
  const colorMap: Record<string, string> = {
    angry: '#ef4444',      // 红色
    rage: '#dc2626',       // 深红
    fear: '#a855f7',       // 紫色
    panic: '#9333ea',      // 深紫
    mock: '#f97316',       // 橙色
    proud: '#eab308',      // 黄色
    arrogant: '#f59e0b',   // 琥珀
    helpless: '#6b7280',   // 灰色
    calm: '#22c55e',       // 绿色
    shock: '#3b82f6',      // 蓝色
    funny: '#ec4899',      // 粉色
    absurd: '#8b5cf6',     // 紫罗兰
    tsundere: '#f472b6',   // 浅粉
  };
  
  return emotion ? (colorMap[emotion] || '#64748b') : '#64748b';
}

// 导出选择器
export const selectCurrentProject = (state: CanvasStore) => state.currentProject;
export const selectNodes = (state: CanvasStore) => state.nodes;
export const selectEdges = (state: CanvasStore) => state.edges;
export const selectSelectedNode = (state: CanvasStore) => 
  state.nodes.find((n) => n.id === state.selectedNodeId);
