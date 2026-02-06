/**
 * CineGraph-AI 状态管理
 * 使用 zustand 管理画布和应用状态
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ==================== 类型定义 ====================

export interface Position {
  x: number;
  y: number;
}

export interface NodeData {
  label: string;
  description?: string;
  type: string;
  content?: string;
  imageUrl?: string;
  videoUrl?: string;
  audioUrl?: string;
  prompt?: string;
  status?: 'pending' | 'processing' | 'completed' | 'error';
  progress?: number;
  createdAt: string;
  [key: string]: any;
}

export interface StudioNode {
  id: string;
  type: string;
  position: Position;
  data: NodeData;
  width?: number;
  height?: number;
  selected?: boolean;
}

export interface StudioEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  animated?: boolean;
  label?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  nodes: StudioNode[];
  edges: StudioEdge[];
  createdAt: string;
  updatedAt: string;
  thumbnail?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  attachments?: {
    type: 'image' | 'video' | 'audio';
    url: string;
    name: string;
  }[];
}

export interface HistoryItem {
  id: string;
  type: 'image' | 'video' | 'audio';
  url: string;
  name: string;
  prompt?: string;
  createdAt: string;
  thumbnail?: string;
}

// ==================== Store 类型 ====================

interface StudioStore {
  // 画布状态
  nodes: StudioNode[];
  edges: StudioEdge[];
  selectedNode: StudioNode | null;
  
  // 工作流
  workflows: Workflow[];
  currentWorkflow: Workflow | null;
  
  // AI 聊天
  chatMessages: ChatMessage[];
  isGenerating: boolean;
  
  // 历史记录
  history: HistoryItem[];
  
  // 设置
  settings: {
    apiKey: string;
    apiProvider: 'pollo' | 'openai' | 'custom';
    theme: 'dark' | 'light';
    language: 'zh' | 'en';
    autoSave: boolean;
  };
  
  // ==================== Actions ====================
  
  // 节点操作
  setNodes: (nodes: StudioNode[]) => void;
  setEdges: (edges: StudioEdge[]) => void;
  addNode: (node: Partial<StudioNode>) => string;
  updateNode: (id: string, data: Partial<NodeData>) => void;
  deleteNode: (id: string) => void;
  setSelectedNode: (node: StudioNode | null) => void;
  
  // 连线操作
  addEdge: (edge: Partial<StudioEdge>) => void;
  deleteEdge: (id: string) => void;
  
  // 工作流操作
  createWorkflow: (name: string, description?: string) => Workflow;
  loadWorkflow: (id: string) => void;
  saveWorkflow: () => void;
  deleteWorkflow: (id: string) => void;
  
  // AI 聊天
  addChatMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  clearChat: () => void;
  
  // AI 生成
  createAINode: (prompt: string, type: 'image' | 'video' | 'text') => Promise<StudioNode | null>;
  generateContent: (prompt: string, type: 'image' | 'video' | 'text') => Promise<string | null>;
  
  // 历史记录
  addToHistory: (item: Omit<HistoryItem, 'id' | 'createdAt'>) => void;
  clearHistory: () => void;
  
  // 设置
  updateSettings: (settings: Partial<StudioStore['settings']>) => void;
  
  // 工具
  undo: () => void;
  redo: () => void;
}

// ==================== Store 实现 ====================

const generateId = () => Math.random().toString(36).substring(2, 15);

export const useStudioStore = create<StudioStore>()(
  persist(
    (set, get) => ({
      // 初始状态
      nodes: [],
      edges: [],
      selectedNode: null,
      
      workflows: [],
      currentWorkflow: null,
      
      chatMessages: [
        {
          id: 'welcome',
          role: 'assistant',
          content: '你好！我是您的创意助手。今天想创作些什么？',
          timestamp: new Date().toISOString(),
        }
      ],
      isGenerating: false,
      
      history: [],
      
      settings: {
        apiKey: '',
        apiProvider: 'pollo',
        theme: 'dark',
        language: 'zh',
        autoSave: true,
      },
      
      // ==================== 节点操作 ====================
      
      setNodes: (nodes) => set({ nodes }),
      
      setEdges: (edges) => set({ edges }),
      
      addNode: (node) => {
        const id = generateId();
        const newNode: StudioNode = {
          id,
          type: node.type || 'default',
          position: node.position || { x: 0, y: 0 },
          data: {
            label: node.data?.label || '未命名节点',
            type: node.type || 'default',
            createdAt: new Date().toISOString(),
            ...node.data,
          },
          width: node.width || 200,
          height: node.height || 100,
        };
        
        set((state) => ({
          nodes: [...state.nodes, newNode],
        }));
        
        return id;
      },
      
      updateNode: (id, data) => {
        set((state) => ({
          nodes: state.nodes.map((n) =>
            n.id === id ? { ...n, data: { ...n.data, ...data } } : n
          ),
        }));
      },
      
      deleteNode: (id) => {
        set((state) => ({
          nodes: state.nodes.filter((n) => n.id !== id),
          edges: state.edges.filter((e) => e.source !== id && e.target !== id),
          selectedNode: state.selectedNode?.id === id ? null : state.selectedNode,
        }));
      },
      
      setSelectedNode: (node) => set({ selectedNode: node }),
      
      // ==================== 连线操作 ====================
      
      addEdge: (edge) => {
        const newEdge: StudioEdge = {
          id: generateId(),
          source: edge.source || '',
          target: edge.target || '',
          type: edge.type || 'default',
          animated: edge.animated || false,
          label: edge.label,
        };
        
        set((state) => ({
          edges: [...state.edges, newEdge],
        }));
      },
      
      deleteEdge: (id) => {
        set((state) => ({
          edges: state.edges.filter((e) => e.id !== id),
        }));
      },
      
      // ==================== 工作流操作 ====================
      
      createWorkflow: (name, description) => {
        const workflow: Workflow = {
          id: generateId(),
          name,
          description,
          nodes: [],
          edges: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        
        set((state) => ({
          workflows: [...state.workflows, workflow],
          currentWorkflow: workflow,
          nodes: [],
          edges: [],
        }));
        
        return workflow;
      },
      
      loadWorkflow: (id) => {
        const workflow = get().workflows.find((w) => w.id === id);
        if (workflow) {
          set({
            currentWorkflow: workflow,
            nodes: workflow.nodes,
            edges: workflow.edges,
          });
        }
      },
      
      saveWorkflow: () => {
        const { currentWorkflow, nodes, edges } = get();
        if (!currentWorkflow) return;
        
        const updatedWorkflow: Workflow = {
          ...currentWorkflow,
          nodes,
          edges,
          updatedAt: new Date().toISOString(),
        };
        
        set((state) => ({
          workflows: state.workflows.map((w) =>
            w.id === currentWorkflow.id ? updatedWorkflow : w
          ),
          currentWorkflow: updatedWorkflow,
        }));
      },
      
      deleteWorkflow: (id) => {
        set((state) => ({
          workflows: state.workflows.filter((w) => w.id !== id),
          currentWorkflow: state.currentWorkflow?.id === id ? null : state.currentWorkflow,
        }));
      },
      
      // ==================== AI 聊天 ====================
      
      addChatMessage: (message) => {
        const newMessage: ChatMessage = {
          ...message,
          id: generateId(),
          timestamp: new Date().toISOString(),
        };
        
        set((state) => ({
          chatMessages: [...state.chatMessages, newMessage],
        }));
      },
      
      clearChat: () => {
        set({
          chatMessages: [
            {
              id: 'welcome',
              role: 'assistant',
              content: '你好！我是您的创意助手。今天想创作些什么？',
              timestamp: new Date().toISOString(),
            }
          ],
        });
      },
      
      // ==================== AI 生成 ====================
      
      createAINode: async (prompt, type) => {
        set({ isGenerating: true });
        
        try {
          // 添加用户消息
          get().addChatMessage({
            role: 'user',
            content: prompt,
          });
          
          // 模拟AI生成（实际应调用后端API）
          await new Promise((resolve) => setTimeout(resolve, 1500));
          
          // 生成节点
          const nodeType = type === 'image' ? 'image-node' : type === 'video' ? 'video-node' : 'text-node';
          const label = type === 'image' ? 'AI 生成图片' : type === 'video' ? 'AI 生成视频' : 'AI 生成文本';
          
          const nodeId = get().addNode({
            type: nodeType,
            position: { x: 300 + Math.random() * 100, y: 200 + Math.random() * 100 },
            data: {
              label,
              type: nodeType,
              prompt,
              content: `正在生成${type === 'image' ? '图片' : type === 'video' ? '视频' : '文本'}...`,
              status: 'processing',
              progress: 0,
              createdAt: new Date().toISOString(),
            },
          });
          
          // 模拟生成完成
          setTimeout(() => {
            get().updateNode(nodeId, {
              status: 'completed',
              progress: 100,
              content: `${type === 'image' ? '图片' : type === 'video' ? '视频' : '文本'}生成完成！`,
            });
          }, 2000);
          
          // 添加AI回复
          get().addChatMessage({
            role: 'assistant',
            content: `已为您生成${type === 'image' ? '图片' : type === 'video' ? '视频' : '文本'}节点。您可以在画布上查看和调整。`,
          });
          
          return get().nodes.find((n) => n.id === nodeId) || null;
        } catch (error) {
          console.error('AI生成失败:', error);
          return null;
        } finally {
          set({ isGenerating: false });
        }
      },
      
      generateContent: async (_prompt, type) => {
        set({ isGenerating: true });
        
        try {
          // 模拟调用后端API
          await new Promise((resolve) => setTimeout(resolve, 2000));
          
          // 返回模拟结果
          const mockResult = type === 'image' 
            ? 'https://example.com/generated-image.png'
            : type === 'video'
            ? 'https://example.com/generated-video.mp4'
            : '生成的文本内容...';
          
          return mockResult;
        } catch (error) {
          console.error('生成失败:', error);
          return null;
        } finally {
          set({ isGenerating: false });
        }
      },
      
      // ==================== 历史记录 ====================
      
      addToHistory: (item) => {
        const newItem: HistoryItem = {
          ...item,
          id: generateId(),
          createdAt: new Date().toISOString(),
        };
        
        set((state) => ({
          history: [newItem, ...state.history],
        }));
      },
      
      clearHistory: () => set({ history: [] }),
      
      // ==================== 设置 ====================
      
      updateSettings: (settings) => {
        set((state) => ({
          settings: { ...state.settings, ...settings },
        }));
      },
      
      // ==================== 工具 ====================
      
      undo: () => {
        // 实现撤销逻辑
        console.log('撤销操作');
      },
      
      redo: () => {
        // 实现重做逻辑
        console.log('重做操作');
      },
    }),
    {
      name: 'cinegraph-store',
      partialize: (state) => ({
        workflows: state.workflows,
        settings: state.settings,
        history: state.history.slice(0, 50), // 只保留最近50条历史
      }),
    }
  )
);
