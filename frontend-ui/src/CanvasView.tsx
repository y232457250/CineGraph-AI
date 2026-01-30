// src/App/CanvasView.tsx
import React, { useRef, useEffect } from 'react';
import ReactFlow, { ReactFlowProvider, Background, Controls, Node, Edge } from 'react-flow';
import 'reactflow/dist/style.css';
import { useNodeStore } from '@/store/nodeStore';
import { useVideoStore, useThumbnailCleanup } from '@/store/videoStore';

// 自定义节点组件
const VideoNode = ({ data }: { data: any }) => {
  useThumbnailCleanup(data.videoPath);
  return (
    <div className="w-full h-full relative">
      <img 
        src={data.thumbnailUrl} 
        className="w-full h-full object-cover"
        alt={data.title}
      />
      <div className="absolute bottom-1 left-1 bg-black/50 text-white text-xs px-1 py-0.5 rounded">
        {data.title}
      </div>
    </div>
  );
};

const CanvasView = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { nodes, edges, addNode, setActiveNode } = useNodeStore();

  // 处理节点点击
  const onNodeClick = (event: React.MouseEvent, node: Node) => {
    event.preventDefault();
    setActiveNode(node.id);
  };

  return (
    <div ref={reactFlowWrapper} className="absolute inset-0 bg-[#1e1e2e] overflow-hidden">
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={{ 'video-node': VideoNode }}
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