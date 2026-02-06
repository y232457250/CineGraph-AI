import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Sparkles, FileText, PenTool, Brain, Loader2 } from 'lucide-react';
import { useStudioStore } from '@/store/studioStore';

interface AIChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (prompt: string, type: 'image' | 'video' | 'text') => Promise<any>;
}

// 快捷功能按钮
const quickActions = [
  { id: 'deep-thinking', icon: <Brain size={14} />, label: '深度思考模式' },
  { id: 'script', icon: <FileText size={14} />, label: '分镜脚本' },
  { id: 'help-write', icon: <PenTool size={14} />, label: '帮我写' },
];

const AIChatPanel: React.FC<AIChatPanelProps> = ({ isOpen, onClose, onGenerate }) => {
  const { chatMessages, isGenerating, addChatMessage } = useStudioStore();
  const [inputValue, setInputValue] = useState('');
  const [selectedType, setSelectedType] = useState<'image' | 'video' | 'text'>('text');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages]);

  // 发送消息
  const handleSend = async () => {
    if (!inputValue.trim() || isGenerating) return;

    const prompt = inputValue.trim();
    setInputValue('');

    // 添加用户消息
    addChatMessage({
      role: 'user',
      content: prompt,
    });

    // 调用生成
    await onGenerate(prompt, selectedType);
  };

  // 处理快捷键
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 添加快捷消息
  const handleQuickAction = (actionId: string) => {
    const prompts: Record<string, string> = {
      'deep-thinking': '请帮我深入分析这个创意概念，提供多个角度的思考...',
      'script': '请帮我写一个分镜脚本，场景是...',
      'help-write': '请帮我完善这段描述...',
    };
    
    setInputValue(prompts[actionId] || '');
    inputRef.current?.focus();
  };

  if (!isOpen) return null;

  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-[#1a1a1a]/95 backdrop-blur-xl border-l border-white/5 z-40 flex flex-col">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
            <Sparkles size={16} className="text-white" />
          </div>
          <div>
            <h3 className="text-white font-medium text-sm">AI 创意助手</h3>
            <p className="text-gray-500 text-xs">提示词优化 & 灵感生成</p>
          </div>
        </div>
        <button 
          onClick={onClose}
          className="w-7 h-7 flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* 聊天消息区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2 mb-4">
          <span className="text-cyan-400 text-xs font-medium uppercase tracking-wider">CINEGRAPH AI</span>
        </div>

        {chatMessages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`
                max-w-[85%] rounded-2xl px-4 py-3 text-sm
                ${message.role === 'user'
                  ? 'bg-cyan-600/20 text-gray-200 rounded-br-md'
                  : 'bg-white/5 text-gray-300 rounded-bl-md'
                }
              `}
            >
              {message.content}
            </div>
          </div>
        ))}

        {/* 生成中指示器 */}
        {isGenerating && (
          <div className="flex justify-start">
            <div className="bg-white/5 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2">
              <Loader2 size={16} className="text-cyan-400 animate-spin" />
              <span className="text-gray-400 text-sm">AI 正在思考...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 底部输入区域 */}
      <div className="p-4 border-t border-white/5 space-y-3">
        {/* 快捷功能按钮 */}
        <div className="flex gap-2">
          {quickActions.map((action) => (
            <button
              key={action.id}
              onClick={() => handleQuickAction(action.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 text-gray-400 text-xs hover:bg-white/10 hover:text-white transition-colors"
            >
              {action.icon}
              {action.label}
            </button>
          ))}
        </div>

        {/* 类型选择 */}
        <div className="flex gap-2">
          {(['text', 'image', 'video'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              className={`
                flex-1 py-2 rounded-lg text-xs font-medium transition-colors
                ${selectedType === type
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'bg-white/5 text-gray-400 hover:bg-white/10'
                }
              `}
            >
              {type === 'text' && '文本'}
              {type === 'image' && '图片'}
              {type === 'video' && '视频'}
            </button>
          ))}
        </div>

        {/* 输入框 */}
        <div className="relative">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的想法，让 AI 为您完善..."
            className="
              w-full bg-white/5 border border-white/10 rounded-xl
              px-4 py-3 pr-12 text-sm text-white placeholder-gray-500
              focus:outline-none focus:border-cyan-500/50
              resize-none min-h-[60px] max-h-[120px]
            "
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isGenerating}
            className="
              absolute right-2 bottom-2
              w-8 h-8 rounded-lg
              flex items-center justify-center
              bg-cyan-500 text-white
              hover:bg-cyan-400
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors
            "
          >
            <Send size={16} />
          </button>
        </div>

        {/* 底部提示 */}
        <p className="text-gray-600 text-xs text-center">
          按 Enter 发送，Shift + Enter 换行
        </p>
      </div>
    </div>
  );
};

export default AIChatPanel;
