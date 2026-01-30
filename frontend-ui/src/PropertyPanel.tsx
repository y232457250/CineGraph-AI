// src/App/PropertyPanel.tsx
import React from 'react';
import { useNodeStore } from '@/store/nodeStore';

const PropertyPanel = () => {
  const { activeNode } = useNodeStore();

  if (!activeNode) return null;

  return (
    <div className="absolute right-4 bottom-4 w-80 bg-[#2d2d3a] rounded-lg p-4 shadow-lg">
      <h3 className="font-bold text-white mb-3">属性设置</h3>
      
      <div className="mb-3">
        <label className="block text-gray-300 mb-1">播放速度</label>
        <input 
          type="range" 
          min="0.5" 
          max="2.0" 
          step="0.1" 
          value={activeNode.playbackRate || 1}
          className="w-full h-2 bg-gray-700 rounded-lg"
        />
      </div>
      
      <div className="mb-3">
        <label className="block text-gray-300 mb-1">音量</label>
        <input 
          type="range" 
          min="0" 
          max="1" 
          step="0.1" 
          value={activeNode.volume || 1}
          className="w-full h-2 bg-gray-700 rounded-lg"
        />
      </div>
      
      <div className="flex justify-between">
        <button className="px-3 py-1 bg-blue-500 text-white rounded">应用</button>
        <button className="px-3 py-1 bg-red-500 text-white rounded">删除</button>
      </div>
    </div>
  );
};

export default PropertyPanel;