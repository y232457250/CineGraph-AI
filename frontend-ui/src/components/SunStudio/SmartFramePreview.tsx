import React from 'react';
import { X, Monitor, Play } from 'lucide-react';

interface SmartFramePreviewProps {
  onClose: () => void;
}

const SmartFramePreview: React.FC<SmartFramePreviewProps> = ({ onClose }) => {
  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center p-8 pointer-events-none">
      {/* 预览卡片 */}
      <div className="w-full max-w-2xl bg-[#0f0f0f] rounded-2xl border border-white/10 overflow-hidden pointer-events-auto shadow-2xl">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
          <h3 className="text-white font-medium text-sm">智能多帧预览</h3>
          <button 
            onClick={onClose}
            className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-white transition-colors rounded hover:bg-white/5"
          >
            <X size={16} />
          </button>
        </div>

        {/* 预览内容 */}
        <div className="aspect-video bg-black flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-4">
              <Monitor size={32} className="text-gray-600" />
            </div>
            <div className="text-gray-500 text-sm">智能多帧预览</div>
            <div className="text-gray-600 text-xs mt-1">选择内容开始预览</div>
          </div>
        </div>
      </div>

      {/* 底部控制栏 */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 pointer-events-auto">
        <div className="flex items-center gap-4 px-6 py-3 bg-[#1a1a1a]/90 backdrop-blur-xl rounded-2xl border border-white/10">
          <button className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-colors">
            <X size={18} />
          </button>
          <div className="w-px h-8 bg-white/10"></div>
          <div className="w-16 h-16 rounded-2xl border-2 border-dashed border-gray-700 flex items-center justify-center">
            <span className="text-gray-600 text-2xl">+</span>
          </div>
          <div className="text-gray-500 text-sm">Add</div>
          <div className="w-px h-8 bg-white/10"></div>
          <button className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-colors">
            <Play size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default SmartFramePreview;
