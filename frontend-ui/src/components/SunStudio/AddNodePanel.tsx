import React from 'react';
import { X, Type, Image, Video, Music, Brain, PenTool } from 'lucide-react';

interface AddNodePanelProps {
  onClose: () => void;
  onAddNode: (type: string, data: any) => void;
}

interface NodeTypeItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  description?: string;
  color: string;
}

const nodeTypes: NodeTypeItem[] = [
  {
    id: 'creative-description',
    icon: <Type size={20} />,
    label: '创意描述',
    description: '添加文本描述节点',
    color: 'from-blue-500/20 to-cyan-500/20',
  },
  {
    id: 'text-to-image',
    icon: <Image size={20} />,
    label: '文字生图',
    description: 'AI 生成图片',
    color: 'from-cyan-500/20 to-teal-500/20',
  },
  {
    id: 'text-to-video',
    icon: <Video size={20} />,
    label: '文生视频',
    description: 'AI 生成视频',
    color: 'from-purple-500/20 to-pink-500/20',
  },
  {
    id: 'inspiration-music',
    icon: <Music size={20} />,
    label: '灵感音乐',
    description: '添加背景音乐',
    color: 'from-orange-500/20 to-amber-500/20',
  },
  {
    id: 'video-analysis',
    icon: <Brain size={20} />,
    label: '视频分析',
    description: '分析视频内容',
    color: 'from-green-500/20 to-emerald-500/20',
  },
  {
    id: 'image-edit',
    icon: <PenTool size={20} />,
    label: '图像编辑',
    description: '编辑图片',
    color: 'from-pink-500/20 to-rose-500/20',
  },
];

const AddNodePanel: React.FC<AddNodePanelProps> = ({ onClose, onAddNode }) => {
  const handleAddNode = (nodeType: NodeTypeItem) => {
    onAddNode(nodeType.id, {
      label: nodeType.label,
      description: nodeType.description,
    });
  };

  return (
    <div className="absolute left-16 top-0 h-full w-72 bg-[#1a1a1a]/95 backdrop-blur-xl border-r border-white/5 z-40 flex flex-col">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <h3 className="text-white font-medium text-sm">添加节点</h3>
        <button 
          onClick={onClose}
          className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-white transition-colors rounded hover:bg-white/5"
        >
          <X size={16} />
        </button>
      </div>

      {/* 节点类型列表 */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {nodeTypes.map((nodeType) => (
          <button
            key={nodeType.id}
            onClick={() => handleAddNode(nodeType)}
            className={`
              w-full flex items-center gap-3 p-3 rounded-xl
              bg-gradient-to-r ${nodeType.color}
              border border-white/5 hover:border-white/20
              transition-all duration-200
              group text-left
            `}
          >
            {/* 图标 */}
            <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center text-gray-300 group-hover:text-white transition-colors">
              {nodeType.icon}
            </div>
            
            {/* 文字 */}
            <div className="flex-1 min-w-0">
              <div className="text-gray-200 text-sm font-medium truncate">
                {nodeType.label}
              </div>
              {nodeType.description && (
                <div className="text-gray-500 text-xs truncate">
                  {nodeType.description}
                </div>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* 底部提示 */}
      <div className="p-3 border-t border-white/5">
        <div className="text-gray-500 text-xs text-center">
          点击节点类型添加到画布
        </div>
      </div>
    </div>
  );
};

export default AddNodePanel;
