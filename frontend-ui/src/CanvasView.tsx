// src/App/CanvasView.tsx
import React, { useRef } from 'react';
import ReactFlow, { ReactFlowProvider, Background, Controls, Node } from 'reactflow';
import 'reactflow/dist/style.css';
import { useThumbnailCleanup } from '@/store/videoStore';

// 自定义节点组件，仍使用缩略图清理 hook
const VideoNode = ({ data }: { data: any }) => {
  useThumbnailCleanup(data?.videoPath);
  return (
    <div className="w-full h-full relative">
      {data?.thumbnailUrl ? (
        <img src={data.thumbnailUrl} className="w-full h-full object-cover" alt={data.title} />
      ) : (
        <div className="w-full h-full bg-gray-800" />
      )}
      <div className="absolute bottom-1 left-1 bg-black/50 text-white text-xs px-1 py-0.5 rounded">
        {data?.title}
      </div>
    </div>
  );
};

const CanvasView = ({
  nodes = [],
  edges = [],
  onNodesChange,
  onNodeClick,
  className
}: {
  nodes?: any[];
  edges?: any[];
  onNodesChange?: (changes: any) => void;
  onNodeClick?: (event: React.MouseEvent, node: Node) => void;
  className?: string;
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  return (
    <div ref={reactFlowWrapper} className={className || 'absolute inset-0 bg-[#1e1e2e] overflow-hidden'}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={{ 'video-node': VideoNode }}
          onNodesChange={onNodesChange}
          onNodeClick={onNodeClick}
          fitView
          minZoom={0.1}
          maxZoom={2}
        >
          <Background />
          <Controls />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
};

export default CanvasView;