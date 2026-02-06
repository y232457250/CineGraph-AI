// frontend-ui/src/components/Canvas/CanvasPage.tsx
/**
 * 无限画布页面
 * 整合项目列表、画布和搜索面板
 */

import React, { useState, useCallback } from 'react';
import InfiniteCanvas from './InfiniteCanvas';
import ProjectList from './ProjectList';
import LineSearchPanel from './LineSearchPanel';
import { useCanvasStore, selectSelectedNode } from '@/store/canvasStore';
import type { CanvasNode } from '@/types/canvas';

interface CanvasPageProps {
  className?: string;
}

const CanvasPage: React.FC<CanvasPageProps> = ({ className }) => {
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>();
  const [showProjectList, setShowProjectList] = useState(true);
  const [showSearchPanel, setShowSearchPanel] = useState(true);
  const [selectedNode, setSelectedNode] = useState<CanvasNode | null>(null);
  
  const currentProject = useCanvasStore((state) => state.currentProject);
  
  const handleProjectSelect = useCallback((projectId: string) => {
    setSelectedProjectId(projectId);
  }, []);
  
  const handleNodeSelect = useCallback((node: CanvasNode | null) => {
    setSelectedNode(node);
  }, []);
  
  return (
    <div className={`flex h-full bg-gray-900 ${className}`}>
      {/* 左侧边栏：项目列表 */}
      {showProjectList && (
        <div className="w-64 border-r border-gray-700 flex flex-col">
          <ProjectList
            onProjectSelect={handleProjectSelect}
            selectedProjectId={selectedProjectId}
            className="flex-1"
          />
          
          {/* 选中节点信息 */}
          {selectedNode && (
            <div className="border-t border-gray-700 p-3">
              <h4 className="text-white text-sm font-medium mb-2">📍 选中节点</h4>
              <div className="text-gray-400 text-xs space-y-1">
                <div><span className="text-gray-500">类型:</span> {selectedNode.node_type}</div>
                <div className="truncate"><span className="text-gray-500">标题:</span> {selectedNode.title}</div>
                {selectedNode.line && (
                  <>
                    <div><span className="text-gray-500">句型:</span> {selectedNode.line.mashup_tags?.sentence_type}</div>
                    <div><span className="text-gray-500">情绪:</span> {selectedNode.line.mashup_tags?.emotion}</div>
                    <div><span className="text-gray-500">强度:</span> {selectedNode.line.intensity}</div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* 中间：画布 */}
      <div className="flex-1 relative">
        {/* 工具栏 */}
        <div className="absolute top-2 left-2 z-10 flex gap-2">
          <button
            onClick={() => setShowProjectList(!showProjectList)}
            className={`
              px-2 py-1 rounded text-xs transition-colors
              ${showProjectList 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }
            `}
          >
            📁 项目
          </button>
          <button
            onClick={() => setShowSearchPanel(!showSearchPanel)}
            className={`
              px-2 py-1 rounded text-xs transition-colors
              ${showSearchPanel 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }
            `}
          >
            🔍 搜索
          </button>
        </div>
        
        {/* 画布内容 */}
        {selectedProjectId ? (
          <InfiniteCanvas
            projectId={selectedProjectId}
            onNodeSelect={handleNodeSelect}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-4xl mb-4">🎬</div>
              <div className="text-gray-400 text-lg mb-2">选择或创建一个项目</div>
              <div className="text-gray-500 text-sm">
                在左侧面板选择现有项目，或点击"新建"创建新项目
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* 右侧边栏：搜索面板 */}
      {showSearchPanel && (
        <LineSearchPanel className="w-72" />
      )}
    </div>
  );
};

export default CanvasPage;

// 导出所有组件
export { InfiniteCanvas, ProjectList, LineSearchPanel };
