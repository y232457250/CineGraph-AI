import React, { useCallback, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Connection,
  useEdgesState,
  addEdge,
  MarkerType,
  NodeTypes,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { 
  Type, Image, Video, Music, Wand2, Loader2, AlertCircle, MoreHorizontal
} from 'lucide-react';
import { StudioNode } from '@/store/studioStore';

// ==================== 自定义节点组件 ====================

interface NodeData {
  label: string;
  description?: string;
  type: string;
  content?: string;
  status?: 'pending' | 'processing' | 'completed' | 'error';
  progress?: number;
  createdAt: string;
  [key: string]: any;
}

// 获取节点图标
const getNodeIcon = (type: string) => {
  switch (type) {
    case 'creative-description':
    case 'text-node':
      return <Type size={18} />;
    case 'text-to-image':
    case 'image-node':
    case 'image-edit':
      return <Image size={18} />;
    case 'text-to-video':
    case 'video-node':
    case 'video-analysis':
      return <Video size={18} />;
    case 'inspiration-music':
      return <Music size={18} />;
    case 'default':
    default:
      return <Wand2 size={18} />;
  }
};

// 获取节点颜色
const getNodeColor = (type: string) => {
  switch (type) {
    case 'creative-description':
    case 'text-node':
      return { bg: 'from-blue-500/20 to-cyan-500/20', border: 'border-blue-500/30', icon: 'text-blue-400' };
    case 'text-to-image':
    case 'image-node':
      return { bg: 'from-cyan-500/20 to-teal-500/20', border: 'border-cyan-500/30', icon: 'text-cyan-400' };
    case 'text-to-video':
    case 'video-node':
      return { bg: 'from-purple-500/20 to-pink-500/20', border: 'border-purple-500/30', icon: 'text-purple-400' };
    case 'inspiration-music':
      return { bg: 'from-orange-500/20 to-amber-500/20', border: 'border-orange-500/30', icon: 'text-orange-400' };
    case 'video-analysis':
      return { bg: 'from-green-500/20 to-emerald-500/20', border: 'border-green-500/30', icon: 'text-green-400' };
    case 'image-edit':
      return { bg: 'from-pink-500/20 to-rose-500/20', border: 'border-pink-500/30', icon: 'text-pink-400' };
    default:
      return { bg: 'from-gray-500/20 to-gray-600/20', border: 'border-gray-500/30', icon: 'text-gray-400' };
  }
};

// 状态指示器
const StatusIndicator = ({ status }: { status?: string; progress?: number }) => {
  if (!status || status === 'completed') return null;
  
  return (
    <div className="absolute -top-2 -right-2">
      {status === 'processing' && (
        <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
          <Loader2 size={14} className="text-white animate-spin" />
        </div>
      )}
      {status === 'error' && (
        <div className="w-6 h-6 rounded-full bg-red-500 flex items-center justify-center">
          <AlertCircle size={14} className="text-white" />
        </div>
      )}
    </div>
  );
};

// 通用节点组件
const StudioNodeComponent: React.FC<{ data: NodeData; selected: boolean }> = ({ data, selected }) => {
  const colors = getNodeColor(data.type);
  
  return (
    <div
      className={`
        relative min-w-[180px] max-w-[280px]
        bg-gradient-to-br ${colors.bg}
        backdrop-blur-xl
        border ${colors.border} ${selected ? 'border-white/50 ring-2 ring-white/20' : ''}
        rounded-xl p-4
        transition-all duration-200
        group
      `}
    >
      {/* 状态指示器 */}
      <StatusIndicator status={data.status} progress={data.progress} />
      
      {/* 连接点 */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-cyan-500 !border-2 !border-[#1a1a1a]"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-cyan-500 !border-2 !border-[#1a1a1a]"
      />
      
      {/* 头部 */}
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center ${colors.icon}`}>
          {getNodeIcon(data.type)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-white text-sm font-medium truncate">
            {data.label}
          </div>
          {data.description && (
            <div className="text-gray-500 text-xs truncate">
              {data.description}
            </div>
          )}
        </div>
      </div>
      
      {/* 内容 */}
      {data.content && (
        <div className="text-gray-300 text-xs line-clamp-3 mt-2 bg-black/20 rounded-lg p-2">
          {data.content}
        </div>
      )}
      
      {/* 进度条 */}
      {data.status === 'processing' && data.progress !== undefined && (
        <div className="mt-2">
          <div className="h-1 bg-white/10 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
              style={{ width: `${data.progress}%` }}
            />
          </div>
          <div className="text-gray-500 text-xs mt-1 text-right">{data.progress}%</div>
        </div>
      )}
      
      {/* 底部工具栏（hover显示） */}
      <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button className="w-6 h-6 rounded bg-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/20">
          <MoreHorizontal size={14} />
        </button>
      </div>
    </div>
  );
};

const nodeTypes: NodeTypes = {
  'default': StudioNodeComponent,
  'creative-description': StudioNodeComponent,
  'text-to-image': StudioNodeComponent,
  'text-to-video': StudioNodeComponent,
  'inspiration-music': StudioNodeComponent,
  'video-analysis': StudioNodeComponent,
  'image-edit': StudioNodeComponent,
  'text-node': StudioNodeComponent,
  'image-node': StudioNodeComponent,
  'video-node': StudioNodeComponent,
};

// ==================== 画布内部组件 ====================

interface SunStudioCanvasInnerProps {
  nodes: StudioNode[];
  edges: Edge[];
  onNodesChange: (changes: any) => void;
  onNodeClick: (node: any) => void;
  onDoubleClick: () => void;
  selectedNode: StudioNode | null;
}

const SunStudioCanvasInner: React.FC<SunStudioCanvasInnerProps> = ({
  nodes,
  onNodesChange,
  onNodeClick,
  onDoubleClick,
  selectedNode,
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [localEdges, setLocalEdges, onEdgesChange] = useEdgesState([]);

  // 转换节点格式
  const flowNodes: Node[] = nodes.map((node) => ({
    id: node.id,
    type: node.type,
    position: node.position,
    data: node.data,
    selected: selectedNode?.id === node.id,
  }));

  // 处理连线
  const onConnect = useCallback((connection: Connection) => {
    setLocalEdges((eds) => addEdge({
      ...connection,
      animated: true,
      style: { stroke: '#06b6d4', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#06b6d4' },
    }, eds));
  }, [setLocalEdges]);

  // 处理节点点击
  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    onNodeClick(node);
  }, [onNodeClick]);

  // 处理画布双击
  const handleDoubleClick = useCallback(() => {
    onDoubleClick();
  }, [onDoubleClick]);

  return (
    <div 
      ref={reactFlowWrapper}
      className="w-full h-full bg-[#0a0a0a]"
      onDoubleClick={handleDoubleClick}
    >
      <ReactFlow
        nodes={flowNodes}
        edges={localEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView={nodes.length > 0}
        minZoom={0.1}
        maxZoom={2}
        snapToGrid
        snapGrid={[20, 20]}
        defaultEdgeOptions={{
          animated: true,
          style: { stroke: '#06b6d4', strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#06b6d4' },
        }}
      >
        <Background 
          color="#1a1a1a" 
          gap={40} 
          size={1}
          style={{ backgroundColor: '#0a0a0a' }}
        />
        <Controls 
          className="bg-[#1a1a1a] border-white/10 [&>button]:bg-[#1a1a1a] [&>button]:border-white/10 [&>button]:text-gray-400 [&>button:hover]:text-white"
        />
        <MiniMap 
          className="bg-[#1a1a1a] border-white/10"
          nodeColor={(n) => {
            const colors = getNodeColor(n.data?.type);
            return colors.icon.includes('cyan') ? '#06b6d4' : 
                   colors.icon.includes('purple') ? '#a855f7' : 
                   colors.icon.includes('orange') ? '#f97316' : 
                   colors.icon.includes('blue') ? '#3b82f6' : '#6b7280';
          }}
          maskColor="rgba(0, 0, 0, 0.8)"
        />
      </ReactFlow>
    </div>
  );
};

// ==================== 主画布组件 ====================

interface SunStudioCanvasProps {
  nodes: StudioNode[];
  edges: Edge[];
  onNodesChange: (changes: any) => void;
  onNodeClick: (node: any) => void;
  onDoubleClick: () => void;
  selectedNode: StudioNode | null;
}

const SunStudioCanvas: React.FC<SunStudioCanvasProps> = (props) => {
  return (
    <ReactFlowProvider>
      <SunStudioCanvasInner {...props} />
    </ReactFlowProvider>
  );
};

export default SunStudioCanvas;
