// src/App/App.tsx
import { useState } from 'react';
import CanvasView from './CanvasView';
import PreviewPanel from './PreviewPanel';
import ResourcePanel from './ResourcePanel';
import TimelinePanel from './TimelinePanel';
import PropertyPanel from './PropertyPanel';
import { Search, Database, LayoutDashboard, Settings } from 'lucide-react';

const SideBarItem = ({ icon, active, onClick, label }: any) => (
  <button
    onClick={onClick}
    className={`p-4 rounded-2xl transition-all group relative ${
      active ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/40' : 'text-gray-500 hover:text-gray-200 hover:bg-white/5'
    }`}
  >
    {icon}
    <span className="absolute left-24 bg-black text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
      {label}
    </span>
  </button>
);

const App = () => {
  const [activeTab, setActiveTab] = useState<'import' | 'canvas' | 'search'>('canvas');

  return (
    <div className="flex h-screen w-screen bg-[#0a0a0a] text-gray-100 overflow-hidden font-sans">
      {/* 左侧侧边栏 */}
      <nav className="w-20 flex flex-col items-center py-8 bg-[#111] border-r border-white/5 space-y-10 z-30">
        <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl flex items-center justify-center font-black text-white shadow-xl shadow-blue-500/20">
          CG
        </div>
        <div className="flex flex-col space-y-4">
          <SideBarItem icon={<Search size={24} />} active={activeTab === 'search'} onClick={() => setActiveTab('search')} label="搜索" />
          <SideBarItem icon={<LayoutDashboard size={24} />} active={activeTab === 'canvas'} onClick={() => setActiveTab('canvas')} label="画布" />
          <SideBarItem icon={<Database size={24} />} active={activeTab === 'import'} onClick={() => setActiveTab('import')} label="入库" />
        </div>
        <div className="flex-grow"></div>
        <SideBarItem icon={<Settings size={24} />} active={false} onClick={() => {}} label="设置" />
      </nav>

      {/* 主区域：画布 & 覆盖面板 */}
      <main className="flex-grow relative overflow-hidden bg-[#080808]">
        {/* Canvas 居中占满 */}
        <div className="absolute inset-0">
          <CanvasView />
        </div>

        {/* 资源面板：左上 */}
        <div className="absolute left-4 top-4 z-40">
          <ResourcePanel />
        </div>

        {/* 预览面板：右上 */}
        <div className="absolute right-4 top-4 z-40">
          <PreviewPanel />
        </div>

        {/* 时间线：底部居中 */}
        <div className="absolute left-4 right-4 bottom-4 z-40">
          <TimelinePanel />
        </div>

        {/* 属性面板：右下 */}
        <div className="absolute right-4 bottom-4 z-50">
          <PropertyPanel />
        </div>
      </main>
    </div>
  );
};

export default App;