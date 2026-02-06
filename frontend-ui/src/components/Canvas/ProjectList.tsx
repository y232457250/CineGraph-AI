// frontend-ui/src/components/Canvas/ProjectList.tsx
/**
 * 画布项目列表组件
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useCanvasStore } from '@/store/canvasStore';
import type { CanvasProject, CreateProjectRequest } from '@/types/canvas';

interface ProjectListProps {
  onProjectSelect: (projectId: string) => void;
  selectedProjectId?: string;
  className?: string;
}

const ProjectList: React.FC<ProjectListProps> = ({
  onProjectSelect,
  selectedProjectId,
  className,
}) => {
  const { projects, loadProjects, createProject, deleteProject, isLoading } = useCanvasStore();
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // 加载项目列表
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);
  
  // 创建项目
  const handleCreate = useCallback(async (data: CreateProjectRequest) => {
    const project = await createProject(data);
    if (project) {
      setShowCreateModal(false);
      onProjectSelect(project.id);
    }
  }, [createProject, onProjectSelect]);
  
  // 删除项目
  const handleDelete = useCallback(async (projectId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('确定要删除这个项目吗？')) {
      await deleteProject(projectId);
    }
  }, [deleteProject]);
  
  return (
    <div className={`bg-gray-800 ${className}`}>
      {/* 标题栏 */}
      <div className="p-3 border-b border-gray-700 flex items-center justify-between">
        <h3 className="text-white font-semibold text-sm">📁 混剪项目</h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded transition-colors"
        >
          + 新建
        </button>
      </div>
      
      {/* 项目列表 */}
      <div className="p-2 space-y-1 max-h-[300px] overflow-y-auto">
        {isLoading ? (
          <div className="text-gray-500 text-xs text-center py-4">加载中...</div>
        ) : projects.length === 0 ? (
          <div className="text-gray-500 text-xs text-center py-4">
            暂无项目，点击新建开始
          </div>
        ) : (
          projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              selected={project.id === selectedProjectId}
              onSelect={() => onProjectSelect(project.id)}
              onDelete={(e) => handleDelete(project.id, e)}
            />
          ))
        )}
      </div>
      
      {/* 创建项目弹窗 */}
      {showCreateModal && (
        <CreateProjectModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  );
};

// ==================== 项目卡片 ====================

interface ProjectCardProps {
  project: CanvasProject;
  selected: boolean;
  onSelect: () => void;
  onDelete: (e: React.MouseEvent) => void;
}

const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  selected,
  onSelect,
  onDelete,
}) => {
  return (
    <div
      onClick={onSelect}
      className={`
        p-2 rounded cursor-pointer transition-all
        ${selected 
          ? 'bg-blue-600/30 border border-blue-500' 
          : 'bg-gray-700/30 border border-transparent hover:bg-gray-700/50'
        }
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="text-white text-sm font-medium truncate">
            {project.name}
          </div>
          {project.description && (
            <div className="text-gray-400 text-xs truncate mt-0.5">
              {project.description}
            </div>
          )}
          <div className="text-gray-500 text-xs mt-1">
            {project.updated_at 
              ? new Date(project.updated_at).toLocaleDateString()
              : '未保存'
            }
          </div>
        </div>
        
        <button
          onClick={onDelete}
          className="text-gray-500 hover:text-red-400 text-xs p-1"
          title="删除项目"
        >
          🗑️
        </button>
      </div>
      
      {/* 主题标签 */}
      {project.theme && (
        <div className="mt-2">
          <span className="px-1.5 py-0.5 bg-purple-500/30 text-purple-300 text-xs rounded">
            {project.theme}
          </span>
        </div>
      )}
    </div>
  );
};

// ==================== 创建项目弹窗 ====================

interface CreateProjectModalProps {
  onClose: () => void;
  onCreate: (data: CreateProjectRequest) => void;
}

const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ onClose, onCreate }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [theme, setTheme] = useState('');
  const [style, setStyle] = useState<'absurd' | 'emotional' | 'suspense'>('absurd');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    
    onCreate({
      name: name.trim(),
      description: description.trim() || undefined,
      theme: theme.trim() || undefined,
      style,
    });
  };
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-4 w-[400px] max-w-[90vw]">
        <h3 className="text-white font-semibold mb-4">新建混剪项目</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 项目名称 */}
          <div>
            <label className="text-gray-400 text-sm block mb-1">
              项目名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：搞笑混剪第1期"
              className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              autoFocus
            />
          </div>
          
          {/* 描述 */}
          <div>
            <label className="text-gray-400 text-sm block mb-1">描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="项目描述（可选）"
              className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none resize-none"
              rows={2}
            />
          </div>
          
          {/* 主题 */}
          <div>
            <label className="text-gray-400 text-sm block mb-1">主题标签</label>
            <input
              type="text"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="例如：甄嬛传、职场、古装"
              className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          
          {/* 风格 */}
          <div>
            <label className="text-gray-400 text-sm block mb-1">混剪风格</label>
            <div className="flex gap-2">
              {[
                { id: 'absurd', name: '🤪 荒诞搞笑' },
                { id: 'emotional', name: '😢 情感共鸣' },
                { id: 'suspense', name: '😱 悬疑紧张' },
              ].map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setStyle(s.id as any)}
                  className={`
                    flex-1 px-3 py-2 rounded text-sm transition-colors
                    ${style === s.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }
                  `}
                >
                  {s.name}
                </button>
              ))}
            </div>
          </div>
          
          {/* 按钮 */}
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={!name.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              创建
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProjectList;
