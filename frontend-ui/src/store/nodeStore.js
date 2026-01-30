// src/store/nodeStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 节点类型定义
export interface NodeData {
  id: string;
  title: string;
  videoPath: string;
  position: { x: number; y: number };
  type: 'video-node' | 'text-node' | 'effect-node';
  duration?: number;
  startTime?: number;
  endTime?: number;
  volume?: number;
  playbackRate?: number;
  thumbnailUrl?: string; // 缓存缩略图URL
}

export interface EdgeData {
  id: string;
  source: string;
  target: string;
  type?: string;
}

interface NodeStore {
  nodes: NodeData[];
  edges: EdgeData[];
  activeNodeId: string | null;
  maxNodes: number; // 节点上限 (内存保护)
  
  // 核心操作
  addNode: (node: NodeData) => void;
  removeNode: (id: string) => void;
  updateNode: (id: string, updates: Partial<NodeData>) => void;
  setActiveNode: (id: string | null) => void;
  addEdge: (edge: EdgeData) => void;
  removeEdge: (id: string) => void;
  
  // 内存优化
  cleanupInactiveNodes: (visibleNodeIds: string[]) => void;
  clearAll: () => void;
}

// 1000节点上限 (12GB显存保护)
const MAX_NODES = 1000;

export const useNodeStore = create<NodeStore>()(
  persist(
    (set, get) => ({
      nodes: [],
      edges: [],
      activeNodeId: null,
      maxNodes: MAX_NODES,
      
      addNode: (node) => {
        set((state) => {
          // 内存保护：超过上限时移除最旧节点
          let newNodes = [...state.nodes, node];
          if (newNodes.length > state.maxNodes) {
            // 释放最旧节点的缩略图资源
            const oldest = newNodes[0];
            if (oldest.thumbnailUrl) {
              URL.revokeObjectURL(oldest.thumbnailUrl);
            }
            newNodes = newNodes.slice(1);
          }
          return { nodes: newNodes };
        });
      },
      
      removeNode: (id) => {
        set((state) => {
          // 释放缩略图资源
          const node = state.nodes.find(n => n.id === id);
          if (node?.thumbnailUrl) {
            URL.revokeObjectURL(node.thumbnailUrl);
          }
          
          return {
            nodes: state.nodes.filter(n => n.id !== id),
            edges: state.edges.filter(e => e.source !== id && e.target !== id),
            activeNodeId: state.activeNodeId === id ? null : state.activeNodeId
          };
        });
      },
      
      updateNode: (id, updates) => {
        set((state) => ({
          nodes: state.nodes.map(n => 
            n.id === id ? { ...n, ...updates } : n
          )
        }));
      },
      
      setActiveNode: (id) => set({ activeNodeId: id }),
      
      addEdge: (edge) => set((state) => ({ 
        edges: [...state.edges, edge] 
      })),
      
      removeEdge: (id) => set((state) => ({ 
        edges: state.edges.filter(e => e.id !== id) 
      })),
      
      // 仅保留可见节点 (滚动时调用)
      cleanupInactiveNodes: (visibleNodeIds) => {
        set((state) => {
          const inactiveNodes = state.nodes.filter(n => !visibleNodeIds.includes(n.id));
          
          // 释放不可见节点的缩略图
          inactiveNodes.forEach(node => {
            if (node.thumbnailUrl) {
              URL.revokeObjectURL(node.thumbnailUrl);
            }
          });
          
          return {
            nodes: state.nodes.map(node => 
              visibleNodeIds.includes(node.id) 
                ? node 
                : { ...node, thumbnailUrl: undefined } // 清除缩略图引用
            )
          };
        });
      },
      
      clearAll: () => {
        // 释放所有缩略图资源
        get().nodes.forEach(node => {
          if (node.thumbnailUrl) URL.revokeObjectURL(node.thumbnailUrl);
        });
        set({ nodes: [], edges: [], activeNodeId: null });
      }
    }),
    {
      name: 'cinegraph-nodes', // 持久化到localStorage
      partialize: (state) => ({ 
        nodes: state.nodes.map(n => ({ ...n, thumbnailUrl: undefined })), // 不持久化缩略图
        edges: state.edges 
      })
    }
  )
);