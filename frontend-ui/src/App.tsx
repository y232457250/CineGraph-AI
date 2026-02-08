import { useState, useCallback, useEffect } from 'react';
import { applyNodeChanges } from '@xyflow/react';
import CanvasView from './CanvasView';
import PreviewPanel from './PreviewPanel';
import TimelinePanel from './TimelinePanel';
import PropertyPanel from './PropertyPanel';
import '@xyflow/react/dist/style.css';
import { Search, LayoutDashboard, Settings, Database } from 'lucide-react';
import ResourcePanel from './ResourcePanel';
import SettingsPanel from './settings';
import { open } from '@tauri-apps/plugin-dialog';


// 初始画布示例节点
const initialNodes = [
  { 
    id: 'welcome', 
    position: { x: 250, y: 150 }, 
    data: { label: '🎬 欢迎使用 CineGraph-AI' },
    style: { background: '#1e1e1e', color: '#fff', border: '1px solid #3b82f6', borderRadius: '12px', padding: '15px', width: 220 }
  },
];

interface AppProps {
  onReady?: () => void;
}

export default function App({ onReady }: AppProps) {
  // --- 状态管理 ---
  const [activeTab, setActiveTab] = useState('search'); // 默认进入搜索页面（侧边栏第一个模块）
  const [showSettings, setShowSettings] = useState(false); // 设置面板显示状态
  const [mediaPath, setMediaPath] = useState('');
  const [movieList, setMovieList] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false); // 全局处理状态
  const [nodes, setNodes] = useState(initialNodes);
  const [edges] = useState([]);
  const [activeNode, setActiveNode] = useState<any | null>(null);

  // 应用加载完成后隐藏启动画面
  useEffect(() => {
    // 等待一小段时间确保渲染完成
    const timer = setTimeout(() => {
      onReady?.();
    }, 300);
    return () => clearTimeout(timer);
  }, [onReady]);

  // 监听打开设置事件（从 ResourcePanel 触发）
  useEffect(() => {
    const handleOpenSettings = (event: CustomEvent) => {
      setShowSettings(true);
      // 可以传递 tab 参数，未来可以用来直接跳转到特定设置页
      console.log('打开设置, tab:', event.detail?.tab);
    };
    
    window.addEventListener('openSettings', handleOpenSettings as EventListener);
    return () => {
      window.removeEventListener('openSettings', handleOpenSettings as EventListener);
    };
  }, []);

  // --- 业务逻辑 0: 获取已保存列表 ---
  const refreshMovieList = useCallback(async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/ingest/list');
      if (response.ok) {
        const data = await response.json();
        // 给每个电影对象添加前端显示状态
        const enhancedList = data.movies.map((m: any) => ({
          ...m,
          stage: m.starring ? 'done' : 'pending' 
        }));
        setMovieList(enhancedList);
      }
    } catch (err) {
      console.error("加载列表失败:", err);
    }
  }, []);

  // --- 画布逻辑 ---
  const onNodesChange = useCallback(
    (changes: any) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [],
  );

  // --- 业务逻辑 1: 批量扫描 ---
  const handleSelectFolder = async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        defaultPath: 'D:\\AI\\CineGraph-AI\\data\\media'
      });
      
      if (selected) {
        setMediaPath(selected);
        setIsProcessing(true);
        
        const response = await fetch('http://127.0.0.1:8000/api/ingest/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selected }),
        });
        
        const data = await response.json();
        // 给每个电影对象添加前端显示状态
        const enhancedList = data.movies.map((m: any) => ({
          ...m,
          stage: m.status === 'ready' ? 'pending' : 'error' 
        }));
        setMovieList(enhancedList);
      }
    } catch (err) {
      console.error("扫描失败:", err);
      alert("无法连接到后端服务，请确保 Python main.py 已启动");
    } finally {
      setIsProcessing(false);
    }
  };

  // --- 业务逻辑 2: 语义标定 (UI 模拟逻辑，待后端完成后接入) ---
  const startWorkflow = async () => {
    if (movieList.length === 0) return;
    setIsProcessing(true);
    // 这里未来会调用后端的 /api/ingest/process 接口
    console.log("启动全量处理流程...");
  };

  // --- 清空扫描列表 ---
  const clearMovieList = useCallback(() => {
    setMovieList([]);
    setMediaPath('');
  }, []);

  return (
    <div className="flex h-screen w-screen bg-[#0a0a0a] text-gray-100 overflow-hidden font-sans">
      
      {/* --- 左侧侧边栏 --- */}
      <nav className="w-20 flex flex-col items-center py-8 bg-[#111] border-r border-white/5 space-y-10 z-30">
        <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl flex items-center justify-center font-black text-white shadow-xl shadow-blue-500/20">
          CG
        </div>
        
        <div className="flex flex-col space-y-4">
          <SideBarItem icon={<Search size={24}/>} active={activeTab === 'search' && !showSettings} onClick={() => { setActiveTab('search'); setShowSettings(false); }} label="搜索" />
          <SideBarItem icon={<LayoutDashboard size={24}/>} active={activeTab === 'canvas' && !showSettings} onClick={() => { setActiveTab('canvas'); setShowSettings(false); }} label="画布" />
          <SideBarItem icon={<Database size={24}/>} active={activeTab === 'import' && !showSettings} onClick={() => { setActiveTab('import'); setShowSettings(false); refreshMovieList(); }} label="入库" />
        </div>
        
        <div className="flex-grow"></div>
        <SideBarItem icon={<Settings size={24}/>} active={showSettings} onClick={() => setShowSettings(!showSettings)} label="设置" />
      </nav>

      {/* --- 主内容显示区 --- */}
      <main className="flex-grow flex flex-col relative overflow-hidden">
        
        {/* 设置面板 */}
        {showSettings && (
          <SettingsPanel />
        )}

        {/* 1. 搜索页面 */}
        {!showSettings && activeTab === 'search' && (
          <div className="p-12 max-w-5xl mx-auto w-full">
            <h1 className="text-4xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-500">
              语义搜索引擎
            </h1>
            <div className="relative group mt-8">
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000"></div>
              <div className="relative flex gap-4 p-3 bg-[#161616] rounded-2xl border border-white/10 shadow-2xl">
                <Search size={24} className="ml-4 self-center text-gray-500" />
                <input 
                  autoFocus
                  placeholder="搜索台词，描述情感、动作或潜台词..." 
                  className="bg-transparent border-none outline-none flex-grow py-4 text-xl placeholder:text-gray-600"
                />
                <button className="bg-blue-600 hover:bg-blue-500 text-white px-10 py-4 rounded-xl font-bold transition-all shadow-lg">
                  检索
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 2. 无限画布页面 */}
        {!showSettings && activeTab === 'canvas' && (
          <div className="w-full h-full relative bg-[#080808]">
            <CanvasView
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onNodeClick={(e, node) => {
                e.preventDefault();
                setActiveNode(node.data || node);
              }}
            />

            {/* 预览面板：右上 */}
            <div className="absolute right-4 top-4 z-40">
              <PreviewPanel activeNode={activeNode} />
            </div>

            {/* 时间线：底部居中 */}
            <div className="absolute left-4 right-4 bottom-4 z-40">
              <TimelinePanel activeNode={activeNode} />
            </div>

            {/* 属性面板：右下 */}
            <div className="absolute right-4 bottom-4 z-50">
              <PropertyPanel activeNode={activeNode} />
            </div>
          </div>
        )}

        {/* 3. 批量入库管理页面 (重点功能) - 使用 CSS 隐藏保持组件状态 */}
        <div className={`w-full h-full ${!showSettings && activeTab === 'import' ? '' : 'hidden'}`}>
          <ResourcePanel
            mediaPath={mediaPath}
            movieList={movieList}
            handleSelectFolder={handleSelectFolder}
            refreshMovieList={refreshMovieList}
            clearMovieList={clearMovieList}
          />
        </div>
      </main>
    </div>
  );
}

// --- 小型封装组件 ---

function SideBarItem({ icon, active, onClick, label }: { icon: any; active: any; onClick: any; label: any }) {
  return (
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
}
