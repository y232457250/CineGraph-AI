// src/App/ResourcePanel.tsx
import React, { useState, useEffect } from 'react';
import { useNodeStore } from '@/store/nodeStore';
import { getMediaFiles } from '@/utils/videoUtils';

const ResourcePanel = () => {
  const [media, setMedia] = useState<any[]>([]);
  const { addNode } = useNodeStore();

  useEffect(() => {
    // 仅加载目录结构 (避免读取大文件)
    getMediaFiles('data/media').then(files => {
      setMedia(files.filter(file => 
        file.type === 'video' || file.type === 'subtitle'
      ));
    });
  }, []);

  const handleAddToCanvas = (file: any) => {
    if (file.type === 'video') {
      addNode({
        id: `video-${Date.now()}`,
        title: file.name,
        videoPath: file.path,
        position: { x: 100, y: 100 },
        type: 'video-node'
      });
    }
  };

  return (
    <div className="absolute left-4 top-4 w-80 h-[calc(100vh-200px)] bg-[#2d2d3a] rounded-lg overflow-hidden shadow-lg">
      <div className="p-3 border-b border-gray-700 font-bold text-white">资源库</div>
      <div className="overflow-y-auto h-full">
        {media.map(file => (
          <div 
            key={file.path} 
            className="p-2 hover:bg-gray-700 cursor-pointer border-b border-gray-800"
            onClick={() => handleAddToCanvas(file)}
          >
            <div className="flex items-center">
              <div className={`w-4 h-4 rounded-full mr-2 ${file.type === 'video' ? 'bg-blue-500' : 'bg-green-500'}`} />
              <span className="truncate">{file.name}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResourcePanel;