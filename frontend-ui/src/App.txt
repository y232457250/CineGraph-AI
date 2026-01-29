import React, { useState, useCallback, useEffect } from 'react';
import { ReactFlow, Background, Controls, applyEdgeChanges, applyNodeChanges } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { 
  Search, Database, LayoutDashboard, Settings, 
  FolderOpen, Play, CheckCircle2, Loader2, 
  Cpu, Zap, Film, FileText 
} from 'lucide-react';
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

export default function App() {
  // --- 状态管理 ---
  const [activeTab, setActiveTab] = useState('import'); // 默认进入入库管理
  const [mediaPath, setMediaPath] = useState('');
  const [movieList, setMovieList] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false); // 全局处理状态
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState([]);

  // --- 画布逻辑 ---
  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
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
        const enhancedList = data.movies.map(m => ({
          ...m,
          stage: m.status === 'ready' ? 'pending' : 'error' // pending(待标定), annotating(标定中), embedding(向量化), done(完成)
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

  return (
    <div className="flex h-screen w-screen bg-[#0a0a0a] text-gray-100 overflow-hidden font-sans">
      
      {/* --- 左侧侧边栏 --- */}
      <nav className="w-20 flex flex-col items-center py-8 bg-[#111] border-r border-white/5 space-y-10 z-30">
        <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl flex items-center justify-center font-black text-white shadow-xl shadow-blue-500/20">
          CG
        </div>
        
        <div className="flex flex-col space-y-4">
          <SideBarItem icon={<Search size={24}/>} active={activeTab === 'search'} onClick={() => setActiveTab('search')} label="搜索" />
          <SideBarItem icon={<LayoutDashboard size={24}/>} active={activeTab === 'canvas'} onClick={() => setActiveTab('canvas')} label="画布" />
          <SideBarItem icon={<Database size={24}/>} active={activeTab === 'import'} onClick={() => setActiveTab('import')} label="入库" />
        </div>
        
        <div className="flex-grow"></div>
        <SideBarItem icon={<Settings size={24}/>} label="设置" />
      </nav>

      {/* --- 主内容显示区 --- */}
      <main className="flex-grow flex flex-col relative overflow-hidden">
        
        {/* 1. 搜索页面 */}
        {activeTab === 'search' && (
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
        {activeTab === 'canvas' && (
          <div className="w-full h-full relative bg-[#080808]">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              colorMode="dark"
              fitView
            >
              <Background color="#222" variant="dots" gap={20} />
              <Controls className="bg-[#1a1a1a] border-white/10" />
            </ReactFlow>
          </div>
        )}

        {/* 3. 批量入库管理页面 (重点功能) */}
        {activeTab === 'import' && (
          <div className="p-10 max-w-6xl w-full h-full overflow-y-auto custom-scrollbar">
            <header className="flex justify-between items-end mb-10">
              <div>
                <h1 className="text-3xl font-bold mb-2">影视库导入</h1>
                <p className="text-gray-400">第一步：扫描目录并提取豆瓣元数据</p>
              </div>
              {movieList.length > 0 && (
                <div className="flex gap-4">
                  <button 
                    onClick={startWorkflow}
                    disabled={isProcessing}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 px-6 py-3 rounded-xl font-bold transition-all"
                  >
                    {isProcessing ? <Loader2 className="animate-spin" size={18} /> : <Zap size={18} />}
                    全量执行 (标定 + 向量化)
                  </button>
                </div>
              )}
            </header>
            
            {/* 路径选择区 */}
            <div className="bg-[#161616] p-8 rounded-3xl border border-white/5 mb-8 shadow-inner">
              <div className="flex justify-between items-center">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-gray-400 text-xs font-bold uppercase tracking-widest">
                    <FolderOpen size={14} /> 当前扫描根目录
                  </div>
                  <div className="text-xl font-mono text-blue-400 break-all">
                    {mediaPath || "等待选择主媒体文件夹..."}
                  </div>
                </div>
                <button 
                  onClick={handleSelectFolder}
                  className="shrink-0 ml-10 bg-white/5 hover:bg-white/10 border border-white/10 px-8 py-4 rounded-2xl font-bold transition-all"
                >
                  选择媒体文件夹
                </button>
              </div>
            </div>

            {/* 扫描结果列表 */}
            {movieList.length > 0 ? (
              <div className="bg-[#111] rounded-3xl border border-white/5 overflow-hidden">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-white/5 text-gray-500 text-[10px] uppercase tracking-[0.2em]">
                      <th className="p-6">豆瓣ID / 文件夹</th>
                      <th className="p-6">影片详情</th>
                      <th className="p-6">文件完整性</th>
                      <th className="p-6">处理进度</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {movieList.map((movie, idx) => (
                      <tr key={idx} className="group hover:bg-white/[0.02] transition-colors">
                        <td className="p-6">
                          <span className="text-xs bg-white/10 px-2 py-1 rounded text-gray-400 font-mono">{movie.douban_id}</span>
                          <div className="mt-2 text-sm text-gray-500 truncate w-40">{movie.folder}</div>
                        </td>
                        <td className="p-6">
                          <div className="font-bold text-lg group-hover:text-blue-400 transition-colors">{movie.title}</div>
                        </td>
                        <td className="p-6 space-y-2">
                          <FileStatus label="视频" exists={!!movie.video_path} icon={<Film size={12}/>} />
                          <FileStatus label="字幕" exists={!!movie.subtitle_path} icon={<FileText size={12}/>} />
                        </td>
                        <td className="p-6">
                          <StageIndicator stage={movie.stage} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              !isProcessing && (
                <div className="h-64 border-2 border-dashed border-white/5 rounded-3xl flex flex-col items-center justify-center text-gray-600">
                  <Database size={48} className="mb-4 opacity-20" />
                  <p>暂无扫描数据，请先选择包含电影文件夹的根目录</p>
                </div>
              )
            )}
          </div>
        )}
      </main>
    </div>
  );
}

// --- 小型封装组件 ---

function SideBarItem({ icon, active, onClick, label }) {
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

function FileStatus({ label, exists, icon }) {
  return (
    <div className={`flex items-center gap-2 text-[11px] font-bold ${exists ? 'text-green-500' : 'text-red-500'}`}>
      <span className="p-1 bg-current/10 rounded">{icon}</span>
      {label}: {exists ? 'READY' : 'MISSING'}
    </div>
  );
}

function StageIndicator({ stage }) {
  const stages = {
    pending: { label: '等待处理', color: 'text-gray-500', icon: <CheckCircle2 size={16} className="opacity-20" /> },
    annotating: { label: '语义标定中...', color: 'text-yellow-500', icon: <Loader2 size={16} className="animate-spin" /> },
    embedding: { label: '向量化中...', color: 'text-blue-500', icon: <Cpu size={16} className="animate-spin" /> },
    done: { label: '已入库', color: 'text-green-500', icon: <CheckCircle2 size={16} /> },
    error: { label: '文件缺失', color: 'text-red-500', icon: null }
  };
  const current = stages[stage] || stages.pending;

  return (
    <div className={`flex items-center gap-2 text-sm font-medium ${current.color}`}>
      {current.icon}
      {current.label}
    </div>
  );
}