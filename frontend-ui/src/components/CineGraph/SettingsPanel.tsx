import React, { useState } from 'react';
import { X, Key, ExternalLink, Check } from 'lucide-react';
import { useStudioStore } from '@/store/studioStore';

interface SettingsPanelProps {
  onClose: () => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ onClose }) => {
  const { settings, updateSettings } = useStudioStore();
  const [apiKey, setApiKey] = useState(settings.apiKey);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    updateSettings({ apiKey });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-[#1a1a1a] rounded-2xl border border-white/10 overflow-hidden">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
              <Key size={16} className="text-gray-400" />
            </div>
            <h3 className="text-white font-medium">设置 (Settings)</h3>
          </div>
          <button 
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-white transition-colors rounded-lg hover:bg-white/5"
          >
            <X size={18} />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="p-6 space-y-6">
          {/* API Key 设置 */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-gray-300 text-sm font-medium">
                AI API KEY
              </label>
              <a 
                href="#" 
                className="text-cyan-400 text-xs hover:underline flex items-center gap-1"
                onClick={(e) => e.preventDefault()}
              >
                获取 Key
                <ExternalLink size={12} />
              </a>
            </div>
            
            <div className="relative">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="key-粘贴您的 API Key..."
                className="
                  w-full bg-[#0a0a0a] border border-white/10 rounded-xl
                  px-4 py-3 text-sm text-white placeholder-gray-600
                  focus:outline-none focus:border-cyan-500/50
                  font-mono
                "
              />
              {saved && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2 text-green-400">
                  <Check size={18} />
                </div>
              )}
            </div>

            <p className="text-gray-500 text-xs mt-3 leading-relaxed">
              用于激活 AI 视频生成模型。
              密钥仅保存在您的浏览器本地存储中，不会上传至 CineGraph-AI 服务器。
            </p>
          </div>

          {/* 主题设置 */}
          <div>
            <label className="text-gray-300 text-sm font-medium block mb-3">
              主题
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => updateSettings({ theme: 'dark' })}
                className={`
                  flex-1 py-2 rounded-lg text-xs font-medium transition-colors
                  ${settings.theme === 'dark'
                    ? 'bg-white text-black'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                  }
                `}
              >
                深色
              </button>
              <button
                onClick={() => updateSettings({ theme: 'light' })}
                className={`
                  flex-1 py-2 rounded-lg text-xs font-medium transition-colors
                  ${settings.theme === 'light'
                    ? 'bg-white text-black'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                  }
                `}
              >
                浅色
              </button>
            </div>
          </div>

          {/* 语言设置 */}
          <div>
            <label className="text-gray-300 text-sm font-medium block mb-3">
              语言
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => updateSettings({ language: 'zh' })}
                className={`
                  flex-1 py-2 rounded-lg text-xs font-medium transition-colors
                  ${settings.language === 'zh'
                    ? 'bg-white text-black'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                  }
                `}
              >
                中文
              </button>
              <button
                onClick={() => updateSettings({ language: 'en' })}
                className={`
                  flex-1 py-2 rounded-lg text-xs font-medium transition-colors
                  ${settings.language === 'en'
                    ? 'bg-white text-black'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                  }
                `}
              >
                English
              </button>
            </div>
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="px-6 py-4 bg-white/5 border-t border-white/5 flex justify-end">
          <button
            onClick={handleSave}
            className="px-6 py-2 bg-white text-black rounded-xl text-sm font-medium hover:bg-gray-200 transition-colors"
          >
            保存设置
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
