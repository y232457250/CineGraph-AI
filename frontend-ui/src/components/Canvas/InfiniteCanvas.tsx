// frontend-ui/src/components/Canvas/InfiniteCanvas.tsx
/**
 * 无限画布组件
 * 基于 ReactFlow 实现，支持：
 * - 节点拖拽和连线
 * - 台词搜索和添加
 * - 接话规则建议
 * - 时间轴预览
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Connection,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  NodeTypes,
  EdgeTypes,
  Panel,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useCanvasStore, selectCurrentProject, selectSelectedNode } from '@/store/canvasStore';
import type { CanvasNode, CanvasEdge, LineData, Position } from '@/types/canvas';

// ==================== 自定义节点组件 ====================

interface ClipNodeData {
  title: string;
  content?: string;
  line?: LineData;
  color?: string;
  intensity?: number;
  emotion?: string;
  sentence_type?: string;
}

const ClipNode: React.FC<{ data: ClipNodeData; selected: boolean }> = ({ data, selected }) => {
  const borderColor = data.color || '#64748b';
  const intensity = data.intensity || 5;
  
  return (
    <div
      className={`
        relative bg-gray-800/90 rounded-lg border-2 p-3 min-w-[180px] max-w-[280px]
        transition-all duration-200 backdrop-blur-sm
        ${selected ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-gray-900' : ''}
      `}
      style={{ borderColor }}
    >
      {/* 强度指示器 */}
      <div 
        className="absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
        style={{ backgroundColor: borderColor }}
      >
        {intensity}
      </div>
      
      {/* 标题 */}
      <div className="text-sm font-medium text-white mb-1 truncate pr-4">
        {data.title}
      </div>
      
      {/* 标签 */}
      <div className="flex flex-wrap gap-1 mb-2">
        {data.sentence_type && (
          <span className="px-1.5 py-0.5 bg-blue-500/30 text-blue-300 text-xs rounded">
            {data.sentence_type}
          </span>
        )}
        {data.emotion && (
          <span className="px-1.5 py-0.5 bg-purple-500/30 text-purple-300 text-xs rounded">
            {data.emotion}
          </span>
        )}
      </div>
      
      {/* 内容 */}
      {data.content && (
        <div className="text-xs text-gray-400 line-clamp-2">
          {data.content}
        </div>
      )}
      
      {/* 连接点 */}
      <div className="absolute left-0 top-1/2 -translate-x-1/2 w-3 h-3 bg-green-500 rounded-full border-2 border-gray-800" />
      <div className="absolute right-0 top-1/2 translate-x-1/2 w-3 h-3 bg-orange-500 rounded-full border-2 border-gray-800" />
    </div>
  );
};

const SceneNode: React.FC<{ data: { title: string; color?: string } }> = ({ data }) => {
  return (
    <div 
      className="bg-gray-700/50 rounded-xl border-2 border-dashed border-gray-500 p-4 min-w-[300px] min-h-[200px]"
      style={{ borderColor: data.color || '#6b7280' }}
    >
      <div className="text-lg font-semibold text-gray-300 mb-2">
        🎬 {data.title}
      </div>
    </div>
  );
};

const NoteNode: React.FC<{ data: { title: string; content?: string } }> = ({ data }) => {
  return (
    <div className="bg-yellow-500/20 rounded-lg border border-yellow-500/50 p-3 max-w-[200px]">
      <div className="text-sm font-medium text-yellow-300 mb-1">📝 {data.title}</div>
      {data.content && (
        <div className="text-xs text-yellow-200/70">{data.content}</div>
      )}
    </div>
  );
};

const nodeTypes: NodeTypes = {
  clip: ClipNode,
  scene: SceneNode,
  note: NoteNode,
};

// ==================== 自定义边组件 ====================

const getEdgeStyle = (relationType?: string) => {
  switch (relationType) {
    case 'escalation':
      return { stroke: '#ef4444', strokeWidth: 3 };
    case 'contrast':
      return { stroke: '#8b5cf6', strokeWidth: 2, strokeDasharray: '5 5' };
    case 'callback':
      return { stroke: '#22c55e', strokeWidth: 2, strokeDasharray: '10 5' };
    default:
      return { stroke: '#64748b', strokeWidth: 2 };
  }
};

// ==================== 主画布组件 ====================

interface InfiniteCanvasProps {
  projectId?: string;
  onNodeSelect?: (node: CanvasNode | null) => void;
}

const InfiniteCanvasInner: React.FC<InfiniteCanvasProps> = ({ projectId, onNodeSelect }) => {
  const reactFlowInstance = useReactFlow();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  
  const {
    currentProject,
    nodes: storeNodes,
    edges: storeEdges,
    selectedNodeId,
    viewport,
    isLoading,
    error,
    loadProject,
    addNode,
    updateNode,
    deleteNode,
    selectNode,
    addEdge: addStoreEdge,
    deleteEdge,
    batchUpdateNodes,
    setViewport,
    saveViewport,
    searchResults,
    suggestedNextLines,
    getNextLines,
    addLineToCanvas,
    clearError,
  } = useCanvasStore();
  
  // 转换为 ReactFlow 格式
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  
  // 加载项目
  useEffect(() => {
    if (projectId && projectId !== currentProject?.id) {
      loadProject(projectId);
    }
  }, [projectId, currentProject?.id, loadProject]);
  
  // 同步 store 节点到 ReactFlow
  useEffect(() => {
    const flowNodes: Node[] = storeNodes.map((n) => ({
      id: n.id,
      type: n.node_type === 'clip' ? 'clip' : n.node_type === 'scene' ? 'scene' : 'note',
      position: { x: n.position.x, y: n.position.y },
      data: {
        title: n.title,
        content: n.content,
        line: n.line,
        color: n.color,
        intensity: n.line?.intensity,
        emotion: n.line?.mashup_tags?.emotion,
        sentence_type: n.line?.mashup_tags?.sentence_type,
      },
      selected: n.id === selectedNodeId,
    }));
    setNodes(flowNodes);
  }, [storeNodes, selectedNodeId, setNodes]);
  
  // 同步 store 边到 ReactFlow
  useEffect(() => {
    const flowEdges: Edge[] = storeEdges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'default',
      animated: e.is_animated,
      label: e.label,
      style: getEdgeStyle(e.relation_type),
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: getEdgeStyle(e.relation_type).stroke,
      },
    }));
    setEdges(flowEdges);
  }, [storeEdges, setEdges]);
  
  // 处理节点变更（拖拽后同步到后端）
  const handleNodesChange = useCallback((changes: any) => {
    onNodesChange(changes);
    
    // 拖拽结束时同步位置
    const positionChanges = changes.filter(
      (c: any) => c.type === 'position' && c.dragging === false && c.position
    );
    
    if (positionChanges.length > 0) {
      const updates = positionChanges.map((c: any) => ({
        id: c.id,
        position: c.position,
      }));
      batchUpdateNodes(updates);
    }
  }, [onNodesChange, batchUpdateNodes]);
  
  // 处理连接
  const handleConnect = useCallback(async (connection: Connection) => {
    if (connection.source && connection.target) {
      const edge = await addStoreEdge({
        source: connection.source,
        target: connection.target,
        relation_type: 'continuation',
      });
      
      if (edge) {
        setEdges((eds) => addEdge({
          ...connection,
          id: edge.id,
          animated: false,
          style: getEdgeStyle('continuation'),
          markerEnd: { type: MarkerType.ArrowClosed },
        }, eds));
      }
    }
  }, [addStoreEdge, setEdges]);
  
  // 处理节点点击
  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    selectNode(node.id);
    
    // 获取下一句建议
    const storeNode = storeNodes.find((n) => n.id === node.id);
    if (storeNode?.line?.id) {
      getNextLines(storeNode.line.id);
    }
    
    onNodeSelect?.(storeNode || null);
  }, [selectNode, storeNodes, getNextLines, onNodeSelect]);
  
  // 处理画布点击（取消选择）
  const handlePaneClick = useCallback(() => {
    selectNode(null);
    onNodeSelect?.(null);
  }, [selectNode, onNodeSelect]);
  
  // 处理拖放添加节点
  const handleDrop = useCallback(async (event: React.DragEvent) => {
    event.preventDefault();
    
    const lineData = event.dataTransfer.getData('application/line');
    if (!lineData) return;
    
    try {
      const line: LineData = JSON.parse(lineData);
      const bounds = reactFlowWrapper.current?.getBoundingClientRect();
      if (!bounds) return;
      
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });
      
      await addLineToCanvas(line, position);
    } catch (e) {
      console.error('添加节点失败:', e);
    }
  }, [reactFlowInstance, addLineToCanvas]);
  
  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);
  
  // 处理视口变更
  const handleMoveEnd = useCallback((_: any, viewport: { x: number; y: number; zoom: number }) => {
    setViewport(viewport);
  }, [setViewport]);
  
  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedNodeId) {
          deleteNode(selectedNodeId);
        }
      }
      if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        saveViewport();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNodeId, deleteNode, saveViewport]);
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900">
        <div className="text-gray-400">加载中...</div>
      </div>
    );
  }
  
  return (
    <div 
      ref={reactFlowWrapper} 
      className="w-full h-full bg-gray-900"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={handleConnect}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        onMoveEnd={handleMoveEnd}
        nodeTypes={nodeTypes}
        defaultViewport={viewport}
        fitView={nodes.length > 0 && !currentProject?.viewport}
        minZoom={0.1}
        maxZoom={2}
        snapToGrid
        snapGrid={[20, 20]}
        connectionLineStyle={{ stroke: '#64748b', strokeWidth: 2 }}
        defaultEdgeOptions={{
          type: 'default',
          markerEnd: { type: MarkerType.ArrowClosed },
        }}
      >
        <Background color="#374151" gap={20} />
        <Controls className="bg-gray-800 border-gray-700" />
        <MiniMap 
          className="bg-gray-800 border-gray-700"
          nodeColor={(n) => n.data?.color || '#64748b'}
          maskColor="rgba(0, 0, 0, 0.8)"
        />
        
        {/* 顶部工具栏 */}
        <Panel position="top-left" className="bg-gray-800/90 rounded-lg p-2 m-2">
          <div className="text-white text-sm font-medium">
            {currentProject?.name || '未命名项目'}
          </div>
          <div className="text-gray-400 text-xs">
            {nodes.length} 个节点 · {edges.length} 条连线
          </div>
        </Panel>
        
        {/* 下一句建议面板 */}
        {selectedNodeId && suggestedNextLines.length > 0 && (
          <Panel position="top-right" className="bg-gray-800/90 rounded-lg p-3 m-2 max-w-[300px]">
            <div className="text-white text-sm font-medium mb-2">💡 接话建议</div>
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {suggestedNextLines.map((line) => (
                <div
                  key={line.id}
                  className="bg-gray-700/50 rounded p-2 cursor-pointer hover:bg-gray-600/50 transition-colors"
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('application/line', JSON.stringify(line));
                  }}
                >
                  <div className="text-xs text-gray-300 line-clamp-2">{line.text}</div>
                  <div className="flex gap-1 mt-1">
                    <span className="text-xs text-blue-400">{line.mashup_tags?.sentence_type}</span>
                    <span className="text-xs text-purple-400">{line.mashup_tags?.emotion}</span>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        )}
        
        {/* 错误提示 */}
        {error && (
          <Panel position="bottom-center" className="bg-red-900/90 rounded-lg p-3 m-2">
            <div className="text-red-200 text-sm flex items-center gap-2">
              <span>❌ {error}</span>
              <button 
                onClick={clearError}
                className="text-red-400 hover:text-red-300"
              >
                ✕
              </button>
            </div>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
};

// 包装 ReactFlowProvider
const InfiniteCanvas: React.FC<InfiniteCanvasProps> = (props) => {
  return (
    <ReactFlowProvider>
      <InfiniteCanvasInner {...props} />
    </ReactFlowProvider>
  );
};

export default InfiniteCanvas;
