import React, { useState } from 'react';
import { X, Image, Video, Clock, Trash2 } from 'lucide-react';
import { useStudioStore } from '@/store/studioStore';

interface HistoryPanelProps {
  onClose: () => void;
}

type TabType = 'image' | 'video';

const HistoryPanel: React.FC<HistoryPanelProps> = ({ onClose }) => {
  const { history, clearHistory } = useStudioStore();
  const [activeTab, setActiveTab] = useState<TabType>('image');

  const filteredHistory = history.filter((item) => item.type === activeTab);

  return (
    <div className="absolute left-16 top-0 h-full w-72 bg-[#1a1a1a]/95 backdrop-blur-xl border-r border-white/5 z-40 flex flex-col">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <h3 className="text-white font-medium text-sm">历史记录</h3>
        <button 
          onClick={onClose}
          className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-white transition-colors rounded hover:bg-white/5"
        >
          <X size={16} />
        </button>
      </div>

      {/* 标签页 */}
      <div className="flex p-2 gap-2">
        <button
          onClick={() => setActiveTab('image')}
          className={`
            flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-medium transition-colors
            ${activeTab === 'image'
              ? 'bg-white/10 text-white'
              : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
            }
          `}
        >
          <Image size={14} />
          图片
        </button>
        <button
          onClick={() => setActiveTab('video')}
          className={`
            flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-medium transition-colors
            ${activeTab === 'video'
              ? 'bg-white/10 text-white'
              : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
            }
          `}
        >
          <Video size={14} />
          视频
        </button>
      </div>

      {/* 历史列表 */}
      <div className="flex-1 overflow-y-auto p-3">
        {filteredHistory.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-4">
            <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
              {activeTab === 'image' ? (
                <Image size={28} className="text-gray-600" />
              ) : (
                <Video size={28} className="text-gray-600" />
              )}
            </div>
            <div className="text-gray-500 text-sm">暂无{activeTab === 'image' ? '图片' : '视频'}</div>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredHistory.map((item) => (
              <div
                key={item.id}
                className="group relative p-2 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-all cursor-pointer"
              >
                {/* 缩略图 */}
                <div className="aspect-video rounded-lg bg-black/50 mb-2 overflow-hidden">
                  {item.thumbnail ? (
                    <img 
                      src={item.thumbnail} 
                      alt={item.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      {item.type === 'image' ? (
                        <Image size={24} className="text-gray-600" />
                      ) : (
                        <Video size={24} className="text-gray-600" />
                      )}
                    </div>
                  )}
                </div>

                {/* 信息 */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-gray-500 text-xs">
                    <Clock size={12} />
                    {new Date(item.createdAt).toLocaleDateString()}
                  </div>
                  <button className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all">
                    <Trash2 size={14} />
                  </button>
                </div>

                {item.prompt && (
                  <div className="text-gray-400 text-xs mt-1 line-clamp-2">
                    {item.prompt}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 清空按钮 */}
      {filteredHistory.length > 0 && (
        <div className="p-3 border-t border-white/5">
          <button
            onClick={clearHistory}
            className="w-full py-2 text-xs text-gray-500 hover:text-red-400 transition-colors"
          >
            清空历史记录
          </button>
        </div>
      )}
    </div>
  );
};

export default HistoryPanel;
