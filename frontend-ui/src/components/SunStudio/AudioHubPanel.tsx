import React from 'react';
import { X, Music, Volume2, Mic, Headphones } from 'lucide-react';

interface AudioHubPanelProps {
  onClose: () => void;
}

const AudioHubPanel: React.FC<AudioHubPanelProps> = ({ onClose }) => {
  const audioCategories = [
    { id: 'bgm', icon: <Music size={18} />, label: '背景音乐', count: 0 },
    { id: 'sfx', icon: <Volume2 size={18} />, label: '音效', count: 0 },
    { id: 'voice', icon: <Mic size={18} />, label: '配音', count: 0 },
    { id: 'ambient', icon: <Headphones size={18} />, label: '环境音', count: 0 },
  ];

  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center p-8">
      {/* 背景遮罩 */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose}></div>

      {/* 面板 */}
      <div className="relative w-full max-w-2xl bg-[#1a1a1a] rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500/20 to-amber-500/20 flex items-center justify-center">
              <Music size={20} className="text-orange-400" />
            </div>
            <div>
              <h3 className="text-white font-medium">音频中心</h3>
              <p className="text-gray-500 text-xs">Audio Hub</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-white transition-colors rounded-lg hover:bg-white/5"
          >
            <X size={18} />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="p-6">
          {/* 分类列表 */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            {audioCategories.map((category) => (
              <button
                key={category.id}
                className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 hover:bg-white/10 transition-all text-left"
              >
                <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center text-gray-400">
                  {category.icon}
                </div>
                <div className="flex-1">
                  <div className="text-gray-200 text-sm font-medium">{category.label}</div>
                  <div className="text-gray-500 text-xs">{category.count} 个项目</div>
                </div>
              </button>
            ))}
          </div>

          {/* 音频波形可视化区域 */}
          <div className="aspect-[3/1] bg-black/50 rounded-xl flex items-center justify-center">
            <div className="flex items-end gap-1 h-16">
              {Array.from({ length: 40 }).map((_, i) => (
                <div
                  key={i}
                  className="w-1.5 bg-gradient-to-t from-orange-500/50 to-amber-500/50 rounded-full"
                  style={{
                    height: `${20 + Math.random() * 60}%`,
                    opacity: 0.3 + Math.random() * 0.7,
                  }}
                />
              ))}
            </div>
          </div>

          {/* 提示文字 */}
          <div className="text-center mt-4">
            <p className="text-gray-500 text-sm">拖拽音频文件到此处，或点击分类浏览</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AudioHubPanel;
