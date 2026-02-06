import React, { useState } from 'react';
import { X, FolderHeart, Plus, Trash2 } from 'lucide-react';
import { useStudioStore } from '@/store/studioStore';

interface WorkflowPanelProps {
  onClose: () => void;
}

const WorkflowPanel: React.FC<WorkflowPanelProps> = ({ onClose }) => {
  const { workflows, currentWorkflow, createWorkflow, loadWorkflow, deleteWorkflow } = useStudioStore();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowDesc, setNewWorkflowDesc] = useState('');

  const handleCreateWorkflow = () => {
    if (newWorkflowName.trim()) {
      createWorkflow(newWorkflowName.trim(), newWorkflowDesc.trim());
      setNewWorkflowName('');
      setNewWorkflowDesc('');
      setShowCreateDialog(false);
    }
  };

  return (
    <div className="absolute left-16 top-0 h-full w-72 bg-[#1a1a1a]/95 backdrop-blur-xl border-r border-white/5 z-40 flex flex-col">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <h3 className="text-white font-medium text-sm">我的工作流</h3>
        <div className="flex items-center gap-1">
          <button 
            onClick={() => setShowCreateDialog(true)}
            className="w-7 h-7 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
          >
            <Plus size={16} />
          </button>
          <button 
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* 工作流列表 */}
      <div className="flex-1 overflow-y-auto p-3">
        {workflows.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-4">
            <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
              <FolderHeart size={28} className="text-gray-600" />
            </div>
            <div className="text-gray-400 text-sm mb-1">空空如也</div>
            <div className="text-gray-600 text-xs">保存您的第一个工作流</div>
          </div>
        ) : (
          <div className="space-y-2">
            {workflows.map((workflow) => (
              <div
                key={workflow.id}
                onClick={() => loadWorkflow(workflow.id)}
                className={`
                  group relative p-3 rounded-xl border cursor-pointer
                  transition-all duration-200
                  ${currentWorkflow?.id === workflow.id 
                    ? 'bg-white/10 border-white/20' 
                    : 'bg-white/5 border-white/5 hover:border-white/10'
                  }
                `}
              >
                <div className="flex items-start gap-3">
                  {/* 图标 */}
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center flex-shrink-0">
                    <FolderHeart size={18} className="text-cyan-400" />
                  </div>
                  
                  {/* 信息 */}
                  <div className="flex-1 min-w-0">
                    <div className="text-gray-200 text-sm font-medium truncate">
                      {workflow.name}
                    </div>
                    {workflow.description && (
                      <div className="text-gray-500 text-xs truncate mt-0.5">
                        {workflow.description}
                      </div>
                    )}
                    <div className="text-gray-600 text-xs mt-1">
                      {workflow.nodes.length} 个节点 · {new Date(workflow.updatedAt).toLocaleDateString()}
                    </div>
                  </div>

                  {/* 删除按钮 */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteWorkflow(workflow.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center text-gray-500 hover:text-red-400 transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 创建对话框 */}
      {showCreateDialog && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="w-full bg-[#1a1a1a] rounded-2xl border border-white/10 p-4">
            <h4 className="text-white font-medium mb-4">新建工作流</h4>
            <input
              type="text"
              placeholder="工作流名称"
              value={newWorkflowName}
              onChange={(e) => setNewWorkflowName(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 mb-3"
              autoFocus
            />
            <input
              type="text"
              placeholder="描述（可选）"
              value={newWorkflowDesc}
              onChange={(e) => setNewWorkflowDesc(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 mb-4"
            />
            <div className="flex gap-2">
              <button
                onClick={() => setShowCreateDialog(false)}
                className="flex-1 py-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleCreateWorkflow}
                className="flex-1 py-2 bg-white text-black rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkflowPanel;
