import React, { useRef, useEffect } from 'react';
import { OceanCanvas, Node, Edge } from '@react-ocean/core';
import { useNodeStore } from '@/store/nodeStore';

const CanvasView = () => {
  const canvasRef = useRef();
  const { nodes, edges } = useNodeStore(); // 状态管理

  useEffect(() => {
    // 初始化OceanCanvas (WebGL加速)
    const canvas = new OceanCanvas(canvasRef.current);
    
    // 优化：仅渲染可见区域
    canvas.setOptimization({
      viewport: { width: window.innerWidth, height: window.innerHeight },
      maxNodes: 500 // 超过自动降级
    });

    return () => {
      canvas.destroy(); // 清理资源
    };
  }, []);

  return (
    <div ref={canvasRef} className="absolute inset-0">
      <OceanCanvas>
        {nodes.map(node => (
          <Node 
            key={node.id}
            id={node.id}
            position={node.position}
            type="video-node" // 自定义节点类型
          >
            <VideoThumbnail videoPath={node.videoPath} /> 
          </Node>
        ))}
        {edges.map(edge => (
          <Edge key={edge.id} source={edge.source} target={edge.target} />
        ))}
      </OceanCanvas>
    </div>
  );
};

// 视频缩略图组件 (避免加载完整视频)
const VideoThumbnail = ({ videoPath }) => {
  const [thumbnail, setThumbnail] = useState('');

  useEffect(() => {
    // 从后端获取缩略图 (FastAPI接口)
    fetch(`/api/video/thumbnail?path=${encodeURIComponent(videoPath)}`)
      .then(res => res.blob())
      .then(blob => setThumbnail(URL.createObjectURL(blob)));
  }, [videoPath]);

  return <img src={thumbnail} className="w-32 h-18 object-cover" />;
};