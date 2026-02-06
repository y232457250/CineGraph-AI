// frontend-ui/src/components/Canvas/LineSearchPanel.tsx
/**
 * 台词搜索面板
 * 用于搜索台词并拖拽添加到画布
 */

import React, { useState, useCallback } from 'react';
import { useCanvasStore } from '@/store/canvasStore';
import type { LineData, SearchLinesParams } from '@/types/canvas';

// ==================== 常量定义 ====================

const SENTENCE_TYPES = [
  { id: 'question', name: '问句', color: '#3b82f6' },
  { id: 'answer', name: '答句', color: '#22c55e' },
  { id: 'command', name: '命令', color: '#ef4444' },
  { id: 'threat', name: '威胁', color: '#dc2626' },
  { id: 'counter_question', name: '反问', color: '#f97316' },
  { id: 'mock', name: '嘲讽', color: '#f59e0b' },
  { id: 'refuse', name: '拒绝', color: '#a855f7' },
  { id: 'fear', name: '害怕', color: '#8b5cf6' },
  { id: 'surrender', name: '求饶', color: '#ec4899' },
  { id: 'counter_attack', name: '反击', color: '#ef4444' },
  { id: 'anger', name: '愤怒', color: '#dc2626' },
  { id: 'reveal', name: '揭示', color: '#06b6d4' },
];

const EMOTIONS = [
  { id: 'angry', name: '愤怒', color: '#ef4444' },
  { id: 'rage', name: '狂怒', color: '#dc2626' },
  { id: 'fear', name: '害怕', color: '#a855f7' },
  { id: 'mock', name: '嘲讽', color: '#f97316' },
  { id: 'proud', name: '得意', color: '#eab308' },
  { id: 'arrogant', name: '嚣张', color: '#f59e0b' },
  { id: 'helpless', name: '无奈', color: '#6b7280' },
  { id: 'calm', name: '冷静', color: '#22c55e' },
  { id: 'shock', name: '震惊', color: '#3b82f6' },
  { id: 'funny', name: '搞笑', color: '#ec4899' },
  { id: 'absurd', name: '荒诞', color: '#8b5cf6' },
  { id: 'tsundere', name: '傲娇', color: '#f472b6' },
];

const TONES = [
  { id: 'strong', name: '强硬' },
  { id: 'weak', name: '软弱' },
  { id: 'provocative', name: '挑衅' },
  { id: 'humble', name: '卑微' },
  { id: 'arrogant', name: '傲慢' },
  { id: 'questioning', name: '质疑' },
  { id: 'certain', name: '肯定' },
  { id: 'pleading', name: '恳求' },
  { id: 'threatening', name: '威胁' },
];

// ==================== 组件 ====================

interface LineSearchPanelProps {
  className?: string;
}

const LineSearchPanel: React.FC<LineSearchPanelProps> = ({ className }) => {
  const { searchResults, searchLines, getHookLines, isLoading } = useCanvasStore();
  
  // 搜索参数
  const [params, setParams] = useState<SearchLinesParams>({
    limit: 50,
  });
  
  // 展开状态
  const [expandedFilters, setExpandedFilters] = useState(false);
  
  // 执行搜索
  const handleSearch = useCallback(() => {
    searchLines(params);
  }, [params, searchLines]);
  
  // 获取钩子台词
  const handleGetHooks = useCallback(() => {
    getHookLines(20);
  }, [getHookLines]);
  
  // 更新参数
  const updateParam = useCallback((key: keyof SearchLinesParams, value: any) => {
    setParams((prev) => ({
      ...prev,
      [key]: value || undefined,
    }));
  }, []);
  
  // 清空参数
  const clearParams = useCallback(() => {
    setParams({ limit: 50 });
  }, []);
  
  // 拖拽开始
  const handleDragStart = useCallback((e: React.DragEvent, line: LineData) => {
    e.dataTransfer.setData('application/line', JSON.stringify(line));
    e.dataTransfer.effectAllowed = 'move';
  }, []);
  
  return (
    <div className={`bg-gray-800 border-l border-gray-700 flex flex-col ${className}`}>
      {/* 标题 */}
      <div className="p-3 border-b border-gray-700">
        <h3 className="text-white font-semibold text-sm">🔍 台词搜索</h3>
        <p className="text-gray-400 text-xs mt-1">拖拽台词到画布添加节点</p>
      </div>
      
      {/* 快捷操作 */}
      <div className="p-3 border-b border-gray-700 flex gap-2">
        <button
          onClick={handleGetHooks}
          className="flex-1 px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white text-xs rounded transition-colors"
        >
          🔥 钩子台词
        </button>
        <button
          onClick={handleSearch}
          disabled={isLoading}
          className="flex-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded transition-colors disabled:opacity-50"
        >
          {isLoading ? '搜索中...' : '搜索'}
        </button>
      </div>
      
      {/* 筛选条件 */}
      <div className="p-3 border-b border-gray-700 space-y-3">
        {/* 关键词 */}
        <div>
          <label className="text-gray-400 text-xs block mb-1">关键词</label>
          <input
            type="text"
            value={params.keyword || ''}
            onChange={(e) => updateParam('keyword', e.target.value)}
            placeholder="输入关键词..."
            className="w-full px-2 py-1.5 bg-gray-700 text-white text-sm rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
          />
        </div>
        
        {/* 句型 */}
        <div>
          <label className="text-gray-400 text-xs block mb-1">句型</label>
          <select
            value={params.sentence_type || ''}
            onChange={(e) => updateParam('sentence_type', e.target.value)}
            className="w-full px-2 py-1.5 bg-gray-700 text-white text-sm rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
          >
            <option value="">全部</option>
            {SENTENCE_TYPES.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
        
        {/* 情绪 */}
        <div>
          <label className="text-gray-400 text-xs block mb-1">情绪</label>
          <select
            value={params.emotion || ''}
            onChange={(e) => updateParam('emotion', e.target.value)}
            className="w-full px-2 py-1.5 bg-gray-700 text-white text-sm rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
          >
            <option value="">全部</option>
            {EMOTIONS.map((e) => (
              <option key={e.id} value={e.id}>{e.name}</option>
            ))}
          </select>
        </div>
        
        {/* 展开更多筛选 */}
        <button
          onClick={() => setExpandedFilters(!expandedFilters)}
          className="text-blue-400 text-xs hover:text-blue-300"
        >
          {expandedFilters ? '收起筛选 ▲' : '更多筛选 ▼'}
        </button>
        
        {expandedFilters && (
          <>
            {/* 语气 */}
            <div>
              <label className="text-gray-400 text-xs block mb-1">语气</label>
              <select
                value={params.tone || ''}
                onChange={(e) => updateParam('tone', e.target.value)}
                className="w-full px-2 py-1.5 bg-gray-700 text-white text-sm rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              >
                <option value="">全部</option>
                {TONES.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            
            {/* 强度 */}
            <div>
              <label className="text-gray-400 text-xs block mb-1">
                最低强度: {params.min_intensity || 1}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={params.min_intensity || 1}
                onChange={(e) => updateParam('min_intensity', parseInt(e.target.value))}
                className="w-full"
              />
            </div>
            
            {/* 最大时长 */}
            <div>
              <label className="text-gray-400 text-xs block mb-1">
                最大时长: {params.max_duration || 10}秒
              </label>
              <input
                type="range"
                min="1"
                max="10"
                step="0.5"
                value={params.max_duration || 10}
                onChange={(e) => updateParam('max_duration', parseFloat(e.target.value))}
                className="w-full"
              />
            </div>
          </>
        )}
        
        {/* 清空按钮 */}
        <button
          onClick={clearParams}
          className="text-gray-400 text-xs hover:text-gray-300"
        >
          清空筛选
        </button>
      </div>
      
      {/* 搜索结果 */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {searchResults.length === 0 ? (
          <div className="text-gray-500 text-xs text-center py-8">
            点击搜索或获取钩子台词
          </div>
        ) : (
          searchResults.map((line) => (
            <LineCard
              key={line.id}
              line={line}
              onDragStart={handleDragStart}
            />
          ))
        )}
      </div>
      
      {/* 底部统计 */}
      <div className="p-2 border-t border-gray-700 text-gray-400 text-xs text-center">
        共 {searchResults.length} 条结果
      </div>
    </div>
  );
};

// ==================== 台词卡片组件 ====================

interface LineCardProps {
  line: LineData;
  onDragStart: (e: React.DragEvent, line: LineData) => void;
}

const LineCard: React.FC<LineCardProps> = ({ line, onDragStart }) => {
  const emotion = EMOTIONS.find((e) => e.id === line.mashup_tags?.emotion);
  const sentenceType = SENTENCE_TYPES.find((t) => t.id === line.mashup_tags?.sentence_type);
  
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, line)}
      className="bg-gray-700/50 rounded-lg p-2 cursor-grab hover:bg-gray-600/50 transition-colors border border-transparent hover:border-gray-500"
    >
      {/* 台词文本 */}
      <div className="text-white text-sm mb-2 line-clamp-2">
        {line.text}
      </div>
      
      {/* 标签 */}
      <div className="flex flex-wrap gap-1 mb-1">
        {sentenceType && (
          <span 
            className="px-1.5 py-0.5 text-xs rounded"
            style={{ 
              backgroundColor: `${sentenceType.color}30`,
              color: sentenceType.color 
            }}
          >
            {sentenceType.name}
          </span>
        )}
        {emotion && (
          <span 
            className="px-1.5 py-0.5 text-xs rounded"
            style={{ 
              backgroundColor: `${emotion.color}30`,
              color: emotion.color 
            }}
          >
            {emotion.name}
          </span>
        )}
        {line.intensity && line.intensity >= 7 && (
          <span className="px-1.5 py-0.5 bg-red-500/30 text-red-400 text-xs rounded">
            🔥 {line.intensity}
          </span>
        )}
      </div>
      
      {/* 来源 */}
      <div className="text-gray-500 text-xs flex items-center gap-2">
        <span>📺 {line.movie}</span>
        {line.duration && (
          <span>⏱ {line.duration.toFixed(1)}s</span>
        )}
      </div>
    </div>
  );
};

export default LineSearchPanel;
