import { useState, useEffect, useCallback, useRef } from 'react';
import { 
  FolderOpen, Database, Film, Loader2, Zap, Search, 
  RefreshCw, FolderInput, X, ChevronDown, Check,
  ChevronRight, FileSearch, Cpu, HardDrive, CheckCircle2, XCircle,
  AlertTriangle, RotateCcw, Trash2, PenSquare
} from 'lucide-react';
import { openPath } from '@tauri-apps/plugin-opener';
import { confirm as confirmDialog } from '@tauri-apps/plugin-dialog';
import useSettingsStore from './store/settingsStore';

// ==================== 类型定义 ====================
interface Movie {
  douban_id: string;
  title: string;
  folder: string;
  video_path?: string;
  subtitle_path?: string;
  video_count?: number;
  subtitle_count?: number;
  director?: string;
  starring?: string[] | string;
  genre?: string;
  language?: string;
  release_date?: string;
  rating?: string;
  media_type?: string;
  poster_url?: string;
  local_poster?: string;
  annotation_path?: string;
  episodes?: Episode[];
  status_import?: 'pending' | 'done' | 'error';
  status_annotate?: 'pending' | 'done' | 'error';
  status_vectorize?: 'pending' | 'done' | 'error';
  vector_path?: string;
  vector_count?: number;
  is_custom?: boolean;  // 标记是否为非豆瓣ID的自定义文件夹
}

interface Episode {
  episode_number: number;
  video_path?: string;
  subtitle_path?: string;
  video_filename?: string;
  subtitle_filename?: string;
  annotation_path?: string;
  vector_path?: string;  // 向量化后的标记
}

interface LLMProvider {
  id: string;
  name: string;
  type: 'local' | 'commercial';
  description: string;
  is_active: boolean;
}

// ==================== 工具组件 ====================

function ProgressBar({ progress, total, label, color = 'blue' }: { progress: number; total: number; label?: string; color?: string }) {
  const percent = total > 0 ? Math.round((progress / total) * 100) : 0;
  const colorClass = color === 'green' ? 'from-green-500 to-emerald-500' : 
                     color === 'purple' ? 'from-purple-500 to-blue-500' : 
                     color === 'pink' ? 'from-pink-500 to-purple-500' :
                     'from-blue-500 to-cyan-500';
  
  return (
    <div className="w-full">
      {label && <div className="text-xs text-gray-400 mb-1">{label}</div>}
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-white/10 h-2 rounded-full overflow-hidden">
          <div 
            className={`h-full bg-gradient-to-r ${colorClass} transition-all duration-300`}
            style={{ width: `${percent}%` }}
          />
        </div>
        <span className="text-xs text-gray-400 w-16 text-right">{progress}/{total}</span>
      </div>
    </div>
  );
}

interface EditMovieForm {
  title: string;
  director: string;
  starring: string;
  genre: string;
  language: string;
  release_date: string;
  rating: string;
  poster_url: string;
}

function EditMovieModal({
  movie,
  form,
  onChange,
  onClose,
  onSubmit,
  saving
}: {
  movie: Movie;
  form: EditMovieForm;
  onChange: (key: keyof EditMovieForm, value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
  saving: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur">
      <div className="w-full max-w-lg bg-[#1a1a1a] border border-white/10 rounded-xl p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">编辑影片信息</h2>
            <p className="text-xs text-gray-500 mt-0.5">{movie.title}</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-white/10 text-gray-400 hover:text-white hover:border-white/30 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <label className="space-y-1">
            <span className="text-xs text-gray-500">标题</span>
            <input
              value={form.title}
              onChange={(e) => onChange('title', e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#121212] border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
              placeholder="影片标题"
            />
          </label>

          <div className="grid grid-cols-2 gap-4">
            <label className="space-y-1">
              <span className="text-xs text-gray-500">导演</span>
              <input
                value={form.director}
                onChange={(e) => onChange('director', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#121212] border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="导演"
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-gray-500">语言</span>
              <input
                value={form.language}
                onChange={(e) => onChange('language', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#121212] border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="语言"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <label className="space-y-1">
              <span className="text-xs text-gray-500">类型</span>
              <input
                value={form.genre}
                onChange={(e) => onChange('genre', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#121212] border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="类型"
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-gray-500">评分</span>
              <input
                value={form.rating}
                onChange={(e) => onChange('rating', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#121212] border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="豆瓣评分"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <label className="space-y-1">
              <span className="text-xs text-gray-500">上映日期</span>
              <input
                value={form.release_date}
                onChange={(e) => onChange('release_date', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#121212] border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="例如：2014-09-30"
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-gray-500">海报地址</span>
              <input
                value={form.poster_url}
                onChange={(e) => onChange('poster_url', e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#121212] border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="图片URL"
              />
            </label>
          </div>

          <label className="space-y-1">
            <span className="text-xs text-gray-500">主演（逗号分隔）</span>
            <textarea
              value={form.starring}
              onChange={(e) => onChange('starring', e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#121212] border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500 min-h-[72px]"
              placeholder="主演1, 主演2, 主演3"
            />
          </label>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
            disabled={saving}
          >
            取消
          </button>
          <button
            onClick={onSubmit}
            disabled={saving}
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white transition-colors"
          >
            {saving ? '保存中...' : '保存修改'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ==================== 影片库卡片组件 ====================
function LibraryMovieCard({
  movie,
  onDeleteEpisode,
  onOpenFolder,
  onEditMovie,
  onDeleteMovie,
  onAnnotateEpisode,
  onVectorizeEpisode,
  onAnnotateMovie,
  onVectorizeMovie
}: {
  movie: Movie;
  onDeleteEpisode?: (movie: Movie, episodeNumber: number) => void;
  onOpenFolder?: (movie: Movie) => void;
  onEditMovie?: (movie: Movie) => void;
  onDeleteMovie?: (movie: Movie) => void;
  onAnnotateEpisode?: (movie: Movie, episode: Episode) => void;
  onVectorizeEpisode?: (movie: Movie, episode: Episode) => void;
  onAnnotateMovie?: (movie: Movie) => void;
  onVectorizeMovie?: (movie: Movie) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasVideo = !!(movie.video_path || (movie.video_count && movie.video_count > 0) || movie.episodes?.some(ep => ep.video_path));
  const hasSubtitle = !!(movie.subtitle_path || (movie.subtitle_count && movie.subtitle_count > 0) || movie.episodes?.some(ep => ep.subtitle_path));
  const hasEpisodeList = Array.isArray(movie.episodes);
  const episodes = hasEpisodeList && movie.episodes ? movie.episodes : [];
  const fallbackCount = hasEpisodeList ? 0 : movie.video_count || 0;
  const episodeCount = hasEpisodeList ? episodes.length : fallbackCount;
  const isSeries = movie.media_type === 'tv' || episodeCount > 1 || (movie.media_type !== 'movie' && episodeCount >= 0 && hasEpisodeList);
  const starringText = Array.isArray(movie.starring) ? movie.starring.join(' / ') : movie.starring || '';

  const hasImportAssets = Boolean(movie.video_path || episodes.length > 0 || movie.subtitle_path);
  const hasAnnotationAssets = Boolean(movie.annotation_path || episodes.some((ep) => ep.annotation_path));
  const hasVectorAssets = Boolean(
    movie.status_vectorize === 'done' ||
    movie.vector_path ||
    (movie.vector_count || 0) > 0
  );

  const statusChips = [
    { label: '导入', value: movie.status_import || (hasImportAssets ? 'done' : 'pending'), icon: FolderInput },
    { label: '标定', value: movie.status_annotate || (hasAnnotationAssets ? 'done' : 'pending'), icon: FileSearch },
    { label: '向量', value: movie.status_vectorize || (hasVectorAssets ? 'done' : hasAnnotationAssets ? 'pending' : 'default'), icon: Cpu }
  ];

  const statusClass = (status?: string) => {
    if (status === 'done') return 'bg-green-500/20 text-green-300 border-green-500/30';
    if (status === 'partial') return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
    if (status === 'error') return 'bg-red-500/15 text-red-300 border-red-500/30';
    if (status === 'pending') return 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30';
    return 'bg-gray-500/10 text-gray-400 border-white/10';
  };

  return (
    <div className="bg-[#1a1a1a] rounded-xl border border-white/5 hover:border-white/15 transition-all">
      <div className="flex items-start gap-3 p-3">
        <div className="w-16 h-24 bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg overflow-hidden shrink-0 flex items-center justify-center">
          {movie.local_poster ? (
            <img 
              src={`http://localhost:8000/api/poster/${encodeURIComponent(movie.local_poster)}`} 
              alt={movie.title} 
              className="w-full h-full object-cover"
              onError={(e) => {
                // 本地图片加载失败时回退到豆瓣图片或默认图标
                const target = e.target as HTMLImageElement;
                if (movie.poster_url) {
                  target.src = movie.poster_url;
                } else {
                  target.style.display = 'none';
                  target.parentElement?.classList.add('show-fallback');
                }
              }}
            />
          ) : movie.poster_url ? (
            <img src={movie.poster_url} alt={movie.title} className="w-full h-full object-cover" />
          ) : (
            <Film size={20} className="text-gray-600" />
          )}
        </div>

        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-white truncate max-w-[60%]">{movie.title || '未知标题'}</h3>
            {isSeries && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded border bg-blue-500/15 text-blue-300 border-blue-500/30 hover:bg-blue-500/25 transition-colors"
              >
                {episodeCount} 集 {isExpanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-gray-500">
            {movie.is_custom ? (
              <span className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">自定义</span>
            ) : (
              <span>豆瓣ID: <span className="text-gray-300">{movie.douban_id}</span></span>
            )}
            <span>年份: <span className="text-gray-300">{movie.release_date?.slice(0, 4) || '-'}</span></span>
            <span>语言: <span className="text-gray-300">{movie.language || '-'}</span></span>
            <span>评分: <span className="text-yellow-400">{movie.rating || '-'}</span></span>
            <span>导演: <span className="text-gray-300">{movie.director || '-'}</span></span>
            <span className="flex items-center gap-1 min-w-0">
              <span>主演:</span>
              <span className="text-gray-300 truncate inline-block max-w-[220px] align-middle" title={starringText || '-'}>{starringText || '-'}</span>
            </span>
            <span className="flex items-center gap-1 min-w-0 text-gray-500">
              <HardDrive size={11} className="text-gray-500" />
              <span 
                className="text-[10px] text-gray-400 font-mono truncate max-w-[300px]" 
                title={(() => {
                  const ep = movie.episodes?.find((e) => e.video_path || e.subtitle_path || e.annotation_path);
                  const path = movie.video_path || movie.subtitle_path || movie.annotation_path || ep?.video_path || ep?.subtitle_path || ep?.annotation_path;
                  if (!path) return movie.folder || '-';
                  const dir = path.replace(/[\\/]+$/, '').replace(/[\\/][^\\/]+$/, '');
                  return dir || movie.folder || '-';
                })()}
              >
                {(() => {
                  const ep = movie.episodes?.find((e) => e.video_path || e.subtitle_path || e.annotation_path);
                  const path = movie.video_path || movie.subtitle_path || movie.annotation_path || ep?.video_path || ep?.subtitle_path || ep?.annotation_path;
                  if (!path) return movie.folder || '-';
                  const dir = path.replace(/[\\/]+$/, '').replace(/[\\/][^\\/]+$/, '');
                  return dir || movie.folder || '-';
                })()}
              </span>
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 text-[11px]">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => onOpenFolder?.(movie)}
                className="flex items-center gap-1 px-2 py-1 rounded-lg border border-blue-500/30 bg-blue-500/15 text-blue-300 hover:bg-blue-500/25 transition-colors"
              >
                <FolderOpen size={11} />
                打开目录
              </button>
              <button
                onClick={() => onEditMovie?.(movie)}
                className="flex items-center gap-1 px-2 py-1 rounded-lg border border-purple-500/30 bg-purple-500/15 text-purple-300 hover:bg-purple-500/25 transition-colors"
              >
                <PenSquare size={11} />
                编辑
              </button>
              <button
                onClick={() => onDeleteMovie?.(movie)}
                className="flex items-center gap-1 px-2 py-1 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 hover:bg-red-500/20 transition-colors"
              >
                <Trash2 size={11} />
                删除
              </button>
              {!hasVideo && (
                <span className="flex items-center gap-1 px-2 py-1 rounded-lg border border-orange-500/30 bg-orange-500/10 text-orange-300">
                  <XCircle size={11} />
                  无影片
                </span>
              )}
              {hasVideo && (
                <span className="flex items-center gap-1 px-2 py-1 rounded-lg border border-green-500/30 bg-green-500/10 text-green-300">
                  <CheckCircle2 size={11} />
                  有影片
                </span>
              )}
              {!hasSubtitle && (
                <span className="flex items-center gap-1 px-2 py-1 rounded-lg border border-yellow-500/30 bg-yellow-500/10 text-yellow-300">
                  <XCircle size={11} />
                  无字幕
                </span>
              )}
              {hasSubtitle && (
                <span className="flex items-center gap-1 px-2 py-1 rounded-lg border border-green-500/30 bg-green-500/10 text-green-300">
                  <CheckCircle2 size={11} />
                  有字幕
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {statusChips.map(({ label, value, icon: Icon }) => {
                const isAnnotateBtn = label === '标定';
                const isVectorizeBtn = label === '向量';
                
                // 标定按钮的可点击逻辑
                let canClickAnnotate = false;
                if (isAnnotateBtn) {
                  // 只有已标定完成（绿色）不可点击，其他情况都允许点击
                  canClickAnnotate = value !== 'done';
                }
                
                const isClickable = (isAnnotateBtn && canClickAnnotate) || isVectorizeBtn;
                
                return (
                  <button
                    key={label}
                    onClick={() => {
                      if (isAnnotateBtn && canClickAnnotate) onAnnotateMovie?.(movie);
                      else if (isVectorizeBtn) onVectorizeMovie?.(movie);
                    }}
                    disabled={!isClickable}
                    className={`flex items-center gap-1 px-2 py-1 border rounded-lg ${statusClass(value)} ${isClickable ? 'cursor-pointer hover:brightness-125 transition-all' : 'cursor-default opacity-60'}`}
                  >
                    <Icon size={12} />
                    <span>{label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {isSeries && isExpanded && (
        <div className="border-t border-white/5 bg-[#121212]">
          <div className="px-4 py-2 text-xs text-gray-500 border-b border-white/5 flex items-center justify-between">
            <span>剧集列表</span>
            <span>{episodes.length} 集</span>
          </div>
          <div className="max-h-56 overflow-y-auto custom-scrollbar">
            {episodes.length > 0 ? (
              episodes.map((ep) => (
                <div
                  key={ep.episode_number}
                  className="flex items-center gap-3 px-4 py-2 hover:bg-white/5 transition-colors"
                >
                  <span className="w-14 text-xs text-gray-500 shrink-0">第{ep.episode_number}集</span>
                  <span className="flex-1 text-xs text-gray-400 truncate" title={ep.video_filename || ep.video_path || ep.subtitle_filename || ep.subtitle_path}>
                    {ep.video_filename || ep.video_path?.split(/[/\\]/).pop() || ep.subtitle_filename || ep.subtitle_path?.split(/[/\\]/).pop() || '-'}
                  </span>
                  {ep.video_path ? (
                    <span className="flex items-center gap-1 text-xs text-green-400">
                      <CheckCircle2 size={10} />
                      <span className="hidden sm:inline">有影片</span>
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-orange-400">
                      <XCircle size={10} />
                      <span className="hidden sm:inline">无影片</span>
                    </span>
                  )}
                  {ep.subtitle_path ? (
                    <span className="flex items-center gap-1 text-xs text-green-400">
                      <CheckCircle2 size={10} />
                      <span className="hidden sm:inline">有字幕</span>
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-red-400">
                      <XCircle size={10} />
                      <span className="hidden sm:inline">无字幕</span>
                    </span>
                  )}
                  <div className="flex items-center gap-1">
                    {/* 标定按钮：颜色与电影卡片一致，已标定不可点击 */}
                    <button
                      onClick={() => {
                        if (!ep.subtitle_path) {
                          alert('没有字幕，无法标定');
                          return;
                        }
                        onAnnotateEpisode?.(movie, ep);
                      }}
                      disabled={Boolean(ep.annotation_path)}
                      className={`px-2 py-1 text-xs border rounded-lg transition-colors ${
                        statusClass(ep.annotation_path ? 'done' : 'pending')
                      } ${ep.annotation_path ? 'cursor-not-allowed' : 'cursor-pointer hover:brightness-125'}`}
                    >
                      {ep.annotation_path ? '已标定' : '标定'}
                    </button>
                    {/* 向量按钮：颜色与电影卡片一致 */}
                    <button
                      onClick={() => onVectorizeEpisode?.(movie, ep)}
                      className={`px-2 py-1 text-xs border rounded-lg transition-colors ${
                        statusClass(movie.status_vectorize || (hasVectorAssets ? 'done' : hasAnnotationAssets ? 'pending' : 'default'))
                      } cursor-pointer hover:brightness-125`}
                    >
                      向量
                    </button>
                    <button
                      onClick={() => onDeleteEpisode?.(movie, ep.episode_number)}
                      className="px-2 py-1 text-xs rounded bg-red-600/70 hover:bg-red-500 text-white transition-colors"
                      title={`删除第${ep.episode_number}集`}
                    >
                      删除
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-4 py-6 text-xs text-gray-500 text-center">暂无剧集数据</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ==================== 主组件 ====================
export default function ResourcePanel({ mediaPath, movieList, handleSelectFolder, refreshMovieList, clearMovieList }: any) {
  const [activeView, setActiveView] = useState<'library' | 'import' | 'annotate' | 'vectorize'>('library');
  
  // 从全局设置获取标注配置、状态控制和当前选中的LLM提供者
  const { 
    annotationConfig, 
    setAnnotationRunning,
    llmProviders: globalLlmProviders,
    activeLLMProvider,
    loadLLMProviders: loadGlobalLLMProviders,
    loadSettingsSections,  // 用于加载标注配置
    // 向量化相关配置
    vectorizationConfig,
    embeddingProviders: globalEmbeddingProviders,
    activeEmbeddingProvider,
    loadEmbeddingProviders: loadGlobalEmbeddingProviders,
  } = useSettingsStore();
  
  // 用于标注轮询的ref
  const annotationPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const annotationCancelRef = useRef(false);
  
  // 用于标记是否已经手动触发过导入，避免切换视图时自动触发
  const importTriggeredRef = useRef(false);
  
  // 缓存标记：避免重复加载影片库
  const libraryLoadedRef = useRef(false);
  
  // 影片库
  const [libraryData, setLibraryData] = useState<Movie[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(true);  // 初始为 true，表示正在加载
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'movie' | 'tv' | 'no-subtitle'>('all');
  
  // 导入流程
  const [importStep, setImportStep] = useState<'idle' | 'scanning' | 'fetching' | 'done' | 'error'>('idle');
  const [scannedItems, setScannedItems] = useState<any[]>([]);
  const [importProgress, setImportProgress] = useState({ current: 0, total: 0, currentItem: '' });
  const [canCancel, setCanCancel] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  
  // 语义标定 - 使用全局状态中的 llmProviders 和 activeLLMProvider（只读显示）
  const llmProviders = globalLlmProviders;
  const selectedProvider = activeLLMProvider;
  
  const [annotationStatus, setAnnotationStatus] = useState<any>(null);
  const [annotationStopping, setAnnotationStopping] = useState(false);
  const [annotationQueueStatus, setAnnotationQueueStatus] = useState({
    current: 0,
    total: 0,
    currentTitle: ''
  });
  const [selectedForAnnotation, setSelectedForAnnotation] = useState<Set<string>>(new Set());
  const [llmConnectionStatus, setLlmConnectionStatus] = useState<'idle' | 'testing' | 'connected' | 'failed'>('idle');
  const [llmConnectionError, setLlmConnectionError] = useState<string>('');
  
  // 向量化
  const [vectorizeStatus, setVectorizeStatus] = useState<any>(null);
  const [selectedForVectorize, setSelectedForVectorize] = useState<Set<string>>(new Set());
  const [vectorizeStopping, setVectorizeStopping] = useState(false);
  const [vectorizeQueueStatus, setVectorizeQueueStatus] = useState({
    current: 0,
    total: 0,
    currentTitle: ''
  });
  const [embeddingConnectionStatus, setEmbeddingConnectionStatus] = useState<'idle' | 'testing' | 'connected' | 'failed'>('idle');
  const [embeddingConnectionError, setEmbeddingConnectionError] = useState<string>('');
  
  // 用于向量化轮询的ref
  const vectorizePollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  
  // 从全局获取当前embedding提供者
  const embeddingProvider = globalEmbeddingProviders.find(p => p.id === activeEmbeddingProvider) || globalEmbeddingProviders.find(p => p.is_active) || null;

  const [editingMovie, setEditingMovie] = useState<Movie | null>(null);
  const [editForm, setEditForm] = useState<EditMovieForm>({
    title: '',
    director: '',
    starring: '',
    genre: '',
    language: '',
    release_date: '',
    rating: '',
    poster_url: ''
  });
  const [savingEdit, setSavingEdit] = useState(false);

  // ==================== 数据加载 ====================
  
  const loadLibrary = async (forceRefresh = false) => {
    // 如果已经加载过且不是强制刷新，直接返回（不管 libraryData 是否为空）
    if (libraryLoadedRef.current && !forceRefresh) {
      setLibraryLoading(false);
      return;
    }
    
    try {
      const res = await fetch('http://127.0.0.1:8000/api/library/list');
      if (res.ok) {
        const data = await res.json();
        setLibraryData(data.items || []);
        libraryLoadedRef.current = true;
      }
    } catch (e) {
      console.error('加载影片库失败:', e);
      if (movieList && movieList.length > 0) {
        setLibraryData(movieList);
      }
    } finally {
      setLibraryLoading(false);
    }
  };

  const isTauriRuntime = () => typeof window !== 'undefined' && Boolean((window as any).__TAURI_INTERNALS__);

  const requestConfirmation = async (message: string, title: string) => {
    if (isTauriRuntime()) {
      try {
        return await confirmDialog(message, { title, kind: 'warning' });
      } catch (err) {
        console.warn('确认对话框调用失败，退回浏览器 confirm:', err);
      }
    }
    if (typeof window !== 'undefined') {
      return window.confirm(message);
    }
    return false;
  };

  // 从 movie 对象中解析出视频/字幕文件所在的目录（完整绝对路径）
  const resolveDirectoryFromMovie = (movie: Movie): string | null => {
    const fallbackEpisode = movie.episodes?.find((ep) => ep.video_path || ep.subtitle_path || ep.annotation_path);
    const rawPath = movie.video_path || movie.subtitle_path || movie.annotation_path || fallbackEpisode?.video_path || fallbackEpisode?.subtitle_path || fallbackEpisode?.annotation_path;
    if (!rawPath) {
      // 如果 folder 本身就是绝对路径
      if (movie.folder && /^[a-zA-Z]:[\\/]/.test(movie.folder)) {
        return movie.folder;
      }
      return null;
    }
    // 去掉尾部分隔符
    const withoutTrailingSeparator = rawPath.replace(/[\\/]+$/, '');
    // 取文件所在的目录（去掉最后的文件名部分）
    const directory = withoutTrailingSeparator.replace(/[\\/][^\\/]+$/, '');
    if (!directory || directory === withoutTrailingSeparator) {
      return withoutTrailingSeparator;
    }
    return directory;
  };

  const handleOpenFolder = async (movie: Movie) => {
    const directory = resolveDirectoryFromMovie(movie);
    console.log('[handleOpenFolder] 解析到的目录:', directory);
    
    if (!directory) {
      alert('未找到可打开的本地目录');
      return;
    }

    try {
      if (isTauriRuntime()) {
        const winPath = directory.replace(/\//g, '\\');
        console.log('[handleOpenFolder] 尝试 openPath:', winPath);
        await openPath(winPath);
        console.log('[handleOpenFolder] openPath 调用成功');
        return;
      }

      if (typeof window !== 'undefined') {
        const normalized = directory.replace(/\\/g, '/');
        window.open(`file:///${normalized}`);
        return;
      }

      alert('当前环境不支持直接打开本地目录');
    } catch (err: unknown) {
      console.error('[handleOpenFolder] 打开目录失败:', err);
      const errorMsg = err instanceof Error ? err.message : String(err);
      alert(`打开目录失败: ${errorMsg}\n路径: ${directory}`);
    }
  };

  const handleEditMovie = (movie: Movie) => {
    const starringValue = Array.isArray(movie.starring) ? movie.starring.join(', ') : (movie.starring || '');
    setEditingMovie(movie);
    setEditForm({
      title: movie.title || '',
      director: movie.director || '',
      starring: starringValue,
      genre: movie.genre || '',
      language: movie.language || '',
      release_date: movie.release_date || '',
      rating: movie.rating || '',
      poster_url: movie.poster_url || ''
    });
  };

  const closeEditModal = () => {
    if (savingEdit) return;
    setEditingMovie(null);
  };

  const handleSaveEdit = async () => {
    if (!editingMovie) return;
    setSavingEdit(true);
    const payload: any = {
      title: editForm.title.trim(),
      director: editForm.director.trim(),
      genre: editForm.genre.trim(),
      language: editForm.language.trim(),
      release_date: editForm.release_date.trim(),
      rating: editForm.rating.trim(),
      poster_url: editForm.poster_url.trim()
    };
    const starringList = editForm.starring
      .split(',')
      .map((name) => name.trim())
      .filter((name) => name.length > 0);
    payload.starring = starringList;

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/library/update/${editingMovie.douban_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || '更新失败');
      }
      await loadLibrary();
      setEditingMovie(null);
    } catch (err: any) {
      console.error('更新影片信息失败:', err);
      alert(err?.message || '更新影片信息失败');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDeleteMovie = async (movie: Movie) => {
    const isTv = movie.media_type === 'tv' || (movie.episodes?.length || 0) > 1;
    const confirmed = await requestConfirmation(
      isTv
        ? `确定要删除《${movie.title}》以及其所有剧集吗？此操作仅会移除索引数据，不会删除原始文件。`
        : `确定要删除《${movie.title}》吗？此操作仅会移除索引数据，不会删除原始文件。`,
      '删除影片'
    );
    if (!confirmed) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/library/delete/${movie.douban_id}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || '删除失败');
      }
      setLibraryLoading(true);
      loadLibrary(true);
    } catch (err: any) {
      console.error('删除影片失败:', err);
      alert(err?.message || '删除影片失败');
    }
  };

  // 单独影片的标定 - 跳转到语义标定页面并选中该影片
  const handleAnnotateMovie = async (movie: Movie) => {
    const isTv = movie.media_type === 'tv' && movie.episodes && movie.episodes.length > 0;
    
    if (isTv) {
      // 电视剧：收集所有有字幕但未标定的剧集
      const pendingEpisodes = movie.episodes?.filter(ep => ep.subtitle_path && !ep.annotation_path) || [];
      
      if (pendingEpisodes.length === 0) {
        // 检查是否有任何字幕
        const hasAnySubtitle = movie.episodes?.some(ep => ep.subtitle_path);
        if (!hasAnySubtitle) {
          alert('没有字幕，无法标定');
        } else {
          alert('该电视剧所有剧集都已完成标定');
        }
        return;
      }
      
      // 选中所有待标定的剧集
      const pendingIds = pendingEpisodes.map(ep => `${movie.douban_id}_ep${ep.episode_number}`);
      setSelectedForAnnotation(new Set(pendingIds));
      setActiveView('annotate');
    } else {
      // 电影
      if (!movie.subtitle_path) {
        alert('没有字幕，无法标定');
        return;
      }
      
      if (movie.annotation_path || movie.status_annotate === 'done') {
        alert('该影片已完成标定');
        return;
      }
      
      setSelectedForAnnotation(new Set([movie.douban_id]));
      setActiveView('annotate');
    }
  };

  // 单独影片的向量化（非电视剧集）- 跳转到向量化页面并选中该影片
  const handleVectorizeMovie = async (movie: Movie) => {
    const annotationFile = movie.annotation_path;
    if (!annotationFile) {
      alert('未找到该影片的标注文件，请先完成语义标定');
      return;
    }
    
    // 跳转到向量化页面，并自动选中该影片
    setSelectedForVectorize(new Set([movie.douban_id]));
    setActiveView('vectorize');
  };

  // 剧集标定 - 跳转到语义标定页面并选中该剧集
  const handleAnnotateEpisode = async (movie: Movie, episode: Episode) => {
    if (!episode.subtitle_path) {
      alert('没有字幕，无法标定');
      return;
    }
    
    if (episode.annotation_path) {
      alert('该集已完成标定');
      return;
    }
    
    // 跳转到语义标定页面，并自动选中该剧集
    setSelectedForAnnotation(new Set([`${movie.douban_id}_ep${episode.episode_number}`]));
    setActiveView('annotate');
  };

  // 剧集向量化 - 跳转到向量化页面并选中该影片
  const handleVectorizeEpisode = async (movie: Movie, episode: Episode) => {
    const annotationFile = episode.annotation_path || movie.annotation_path;
    if (!annotationFile) {
      alert('未找到该集的标注文件，请先完成语义标定');
      return;
    }
    
    // 跳转到向量化页面，并自动选中该影片
    setSelectedForVectorize(new Set([movie.douban_id]));
    setActiveView('vectorize');
  };

  // 使用全局store加载LLM提供者
  const loadLLMProviders = async (): Promise<LLMProvider[]> => {
    return loadGlobalLLMProviders();
  };

  // LLM连接测试
  const testLLMConnection = async (providerId: string): Promise<boolean> => {
    if (!providerId) {
      setLlmConnectionStatus('idle');
      return false;
    }
    
    setLlmConnectionStatus('testing');
    setLlmConnectionError('');
    
    try {
      const res = await fetch('http://127.0.0.1:8000/api/annotation/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: providerId })
      });
      
      const data = await res.json();
      
      if (res.ok && data.success) {
        setLlmConnectionStatus('connected');
        return true;
      } else {
        setLlmConnectionStatus('failed');
        setLlmConnectionError(data.error || '连接失败');
        return false;
      }
    } catch (e: any) {
      setLlmConnectionStatus('failed');
      setLlmConnectionError(e.message || '网络错误');
      return false;
    }
  };

  useEffect(() => {
    loadLibrary();
    loadLLMProviders();
    // 如果标注配置未加载，立即加载（确保启动时就有正确的配置）
    if (!annotationConfig._loaded) {
      loadSettingsSections();
    }
  }, []);

  useEffect(() => {
    if (activeView === 'library') {
      // 如果已经加载过，不需要再加载
      if (!libraryLoadedRef.current) {
        setLibraryLoading(true);
        loadLibrary();
      }
    } else if (activeView === 'import') {
      // 彻底重置导入状态
      setImportStep('idle');
      setScannedItems([]);
      setImportProgress({ current: 0, total: 0, currentItem: '' });
      // 重置触发标记，确保只有用户主动选择文件夹后才触发导入
      importTriggeredRef.current = false;
      // 清空父组件的扫描列表
      clearMovieList?.();
    } else if (activeView === 'annotate') {
      loadLLMProviders().then(() => {
        // 加载后自动测试当前选中的模型连接
        if (selectedProvider) {
          testLLMConnection(selectedProvider);
        }
      });
      // 如果已加载过就不重复加载
      if (!libraryLoadedRef.current) {
        loadLibrary();
      }
      // 恢复标注状态：从后端获取当前运行状态
      fetchAnnotationStatus();
    } else if (activeView === 'vectorize') {
      // 如果已加载过就不重复加载
      if (!libraryLoadedRef.current) {
        loadLibrary();
      }
    }
  }, [activeView, clearMovieList]);

  // 从后端获取标注状态（用于视图切换时恢复UI状态）
  const fetchAnnotationStatus = useCallback(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/annotation/status');
      if (res.ok) {
        const status = await res.json();
        // 只有当后端正在运行时才恢复状态
        if (status.running) {
          setAnnotationStatus(status);
          setAnnotationRunning(true);
          // 如果正在运行，启动轮询
          startAnnotationPolling();
        }
      }
    } catch (e) {
      console.error('获取标注状态失败:', e);
    }
  }, [setAnnotationRunning]);

  // 标注状态轮询
  const startAnnotationPolling = useCallback(() => {
    // 清除之前的轮询
    if (annotationPollRef.current) {
      clearInterval(annotationPollRef.current);
    }
    
    annotationPollRef.current = setInterval(async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/annotation/status');
        if (res.ok) {
          const status = await res.json();
          setAnnotationStatus(status);
          if (!status.running) {
            if (annotationPollRef.current) {
              clearInterval(annotationPollRef.current);
              annotationPollRef.current = null;
            }
            setAnnotationRunning(false);
            // 强制刷新影片库以更新标定状态
            loadLibrary(true);
          }
        }
      } catch (e) {
        console.error('轮询标注状态失败:', e);
      }
    }, 2000);
  }, [setAnnotationRunning]);

  // 组件卸载时清理轮询
  useEffect(() => {
    return () => {
      if (annotationPollRef.current) {
        clearInterval(annotationPollRef.current);
      }
    };
  }, []);

  // 注意：影片库数据(libraryData)和导入扫描数据(scannedItems/movieList)是分开的
  // - libraryData: 从后端 /api/library/list 加载，代表已持久化的数据
  // - scannedItems/movieList: 当前扫描的临时数据，导入完成后会保存到后端
  // 导入完成后，通过 loadLibrary() 刷新影片库

  // ==================== 导入流程 ====================
  
  const handleSelectAndScan = async () => {
    setScannedItems([]);
    setImportProgress({ current: 0, total: 0, currentItem: '' });
    setImportStep('idle');
    setExpandedItems(new Set());
    // 标记为用户主动触发
    importTriggeredRef.current = true;
    await handleSelectFolder();
  };

  // 扫描完成后自动显示结果并开始导入
  // 只有当用户主动选择文件夹后（importTriggeredRef.current = true）才会触发
  useEffect(() => {
    if (activeView === 'import' && movieList && movieList.length > 0 && importStep === 'idle' && importTriggeredRef.current) {
      setScannedItems(movieList);
      // 自动开始导入和抓取
      setImportStep('fetching');
      setCanCancel(true);
      
      // 异步执行导入
      (async () => {
        try {
          const res = await fetch('http://127.0.0.1:8000/api/ingest/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(movieList)
          });
          
          if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || '保存失败');
          }

          const enrichRes = await fetch('http://127.0.0.1:8000/api/ingest/enrich/start', { method: 'POST' });
          if (!enrichRes.ok) {
            throw new Error('启动抓取失败');
          }

          // 轮询进度
          const pollId = setInterval(async () => {
            try {
              const statusRes = await fetch('http://127.0.0.1:8000/api/ingest/enrich/status');
              if (statusRes.ok) {
                const status = await statusRes.json();
                setImportProgress({
                  current: status.processed || 0,
                  total: status.total || 0,
                  currentItem: status.current?.title || ''
                });

                if (status.status === 'done') {
                  clearInterval(pollId);
                  setImportStep('done');
                  setCanCancel(false);
                  setLibraryLoading(true);
                  loadLibrary(true);
                } else if (status.status === 'error') {
                  clearInterval(pollId);
                  setImportStep('error');
                  setCanCancel(false);
                }
              }
            } catch (e) {
              console.error('轮询状态失败:', e);
            }
          }, 1000);

        } catch (err: any) {
          console.error('导入失败:', err);
          setImportStep('error');
          setCanCancel(false);
        }
      })();
    }
  }, [movieList, activeView, importStep]);

  const cancelImport = async () => {
    try {
      await fetch('http://127.0.0.1:8000/api/ingest/enrich/cancel', { method: 'POST' });
      setImportStep('idle');
      setCanCancel(false);
    } catch (e) {
      console.error('取消失败:', e);
    }
  };

  // ==================== 语义标定 ====================
  
  const startAnnotation = async () => {
    if (selectedForAnnotation.size === 0 || !selectedProvider) {
      alert('请选择要标定的影片和AI模型');
      return;
    }

    // 收集所有需要标注的字幕文件（支持剧集单选和整剧标定）
    const subtitleTasksMap = new Map<string, {movie_id: string, subtitle_path: string, movie_name: string, episode?: number}>();
    const selectedKeys = Array.from(selectedForAnnotation);

    const addTask = (task: {movie_id: string, subtitle_path: string, movie_name: string, episode?: number}) => {
      if (!subtitleTasksMap.has(task.movie_id)) {
        subtitleTasksMap.set(task.movie_id, task);
      }
    };

    selectedKeys.forEach((key) => {
      if (key.includes('_ep')) {
        const [movieId, epPart] = key.split('_ep');
        const epNumber = Number(epPart);
        const movie = libraryData.find((m) => m.douban_id === movieId);
        const episode = movie?.episodes?.find((ep) => ep.episode_number === epNumber);
        if (movie && episode?.subtitle_path) {
          addTask({
            movie_id: `${movieId}_ep${epNumber}`,
            subtitle_path: episode.subtitle_path,
            movie_name: `${movie.title} 第${epNumber}集`,
            episode: epNumber
          });
        }
      } else {
        const movie = libraryData.find((m) => m.douban_id === key);
        if (!movie) return;

        // 电视剧：标定所有有字幕的剧集
        if (movie.media_type === 'tv' && movie.episodes && movie.episodes.length > 0) {
          movie.episodes.forEach((ep) => {
            if (ep.subtitle_path) {
              addTask({
                movie_id: `${movie.douban_id}_ep${ep.episode_number}`,
                subtitle_path: ep.subtitle_path,
                movie_name: `${movie.title} 第${ep.episode_number}集`,
                episode: ep.episode_number
              });
            }
          });
        } else if (movie.subtitle_path) {
          // 电影：单个字幕文件
          addTask({
            movie_id: movie.douban_id,
            subtitle_path: movie.subtitle_path,
            movie_name: movie.title
          });
        }
      }
    });

    const subtitleTasks = Array.from(subtitleTasksMap.values());
    
    if (subtitleTasks.length === 0) {
      alert('所选影片没有可用的字幕文件');
      return;
    }
    
    console.log(`开始标注 ${subtitleTasks.length} 个字幕文件，配置: batch_size=${annotationConfig.batch_size}, concurrent=${annotationConfig.concurrent_requests}`);
    annotationCancelRef.current = false;
    setAnnotationStopping(false);
    setAnnotationQueueStatus({
      current: 0,
      total: subtitleTasks.length,
      currentTitle: ''
    });
    
    // 设置全局标注运行状态（禁用设置页模型切换）
    setAnnotationRunning(true);
    
    let processedCount = 0;

    // 依次标注每个字幕文件
    for (let i = 0; i < subtitleTasks.length; i++) {
      if (annotationCancelRef.current) {
        break;
      }
      const task = subtitleTasks[i];
      
      try {
        setAnnotationQueueStatus({
          current: i,
          total: subtitleTasks.length,
          currentTitle: task.movie_name
        });
        setAnnotationStatus({
          running: true,
          progress: 0,
          total: 0,
          current_movie: `[${i + 1}/${subtitleTasks.length}] ${task.movie_name}`,
          error: null
        });
        
        const res = await fetch('http://127.0.0.1:8000/api/annotation/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            movie_id: task.movie_id,
            subtitle_path: task.subtitle_path,
            movie_name: task.movie_name,
            llm_provider: selectedProvider,
            // 传递标注配置参数
            batch_size: annotationConfig.batch_size,
            concurrent_requests: annotationConfig.concurrent_requests,
            max_retries: annotationConfig.max_retries,
            save_interval: annotationConfig.save_interval
          })
        });

        if (res.ok) {
          // 等待当前任务完成
          await new Promise<void>((resolve) => {
            if (annotationPollRef.current) {
              clearInterval(annotationPollRef.current);
            }
            const pollAnnotation = setInterval(async () => {
              try {
                const statusRes = await fetch('http://127.0.0.1:8000/api/annotation/status');
                if (statusRes.ok) {
                  const status = await statusRes.json();
                  setAnnotationStatus({
                    ...status,
                    current_movie: `[${i + 1}/${subtitleTasks.length}] ${task.movie_name}`
                  });
                  if (!status.running) {
                    clearInterval(pollAnnotation);
                    annotationPollRef.current = null;
                    resolve();
                  }
                }
              } catch (e) {
                console.error('轮询状态失败:', e);
              }
            }, 2000);
            annotationPollRef.current = pollAnnotation;
          });
        }
      } catch (e) {
        console.error(`标注失败: ${task.movie_name}`, e);
      }
      setAnnotationQueueStatus({
        current: i + 1,
        total: subtitleTasks.length,
        currentTitle: task.movie_name
      });
      processedCount = i + 1;
      if (annotationCancelRef.current) {
        break;
      }
    }
    
    // 全部完成
    // 全部完成，重置全局标注状态
    setAnnotationRunning(false);
    const finishedCount = annotationCancelRef.current
      ? processedCount
      : subtitleTasks.length;
    setAnnotationStatus({
      running: false,
      progress: finishedCount,
      total: subtitleTasks.length,
      current_movie: annotationCancelRef.current ? '已停止' : '全部完成',
      error: null
    });
    setAnnotationQueueStatus({
      current: annotationCancelRef.current ? processedCount : subtitleTasks.length,
      total: subtitleTasks.length,
      currentTitle: annotationCancelRef.current ? '已停止' : '全部完成'
    });
    setAnnotationStopping(false);
    // 强制刷新影片库以更新标定状态
    await loadLibrary(true);
    // 清空已选择的标定项（因为已经完成）
    setSelectedForAnnotation(new Set());
  };

  const stopAnnotation = async () => {
    if (!annotationStatus?.running) return;
    annotationCancelRef.current = true;
    setAnnotationStopping(true);
    try {
      await fetch('http://127.0.0.1:8000/api/annotation/cancel', { method: 'POST' });
    } catch (e) {
      console.error('取消标注失败:', e);
    }
    if (annotationPollRef.current) {
      clearInterval(annotationPollRef.current);
      annotationPollRef.current = null;
    }
    setAnnotationStatus((prev: any) => ({
      ...prev,
      running: false,
      current_movie: '已停止',
      error: '已取消'
    }));
    setAnnotationRunning(false);
    setAnnotationStopping(false);
    await loadLibrary(true);
    setSelectedForAnnotation(new Set());
  };

  // ==================== 向量化 ====================
  
  // 测试embedding连接
  const testEmbeddingConnection = async () => {
    if (!activeEmbeddingProvider) {
      setEmbeddingConnectionStatus('idle');
      return;
    }
    
    setEmbeddingConnectionStatus('testing');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/settings/embedding/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: activeEmbeddingProvider })
      });
      const result = await res.json();
      
      if (result.success) {
        setEmbeddingConnectionStatus('connected');
        setEmbeddingConnectionError('');
      } else {
        setEmbeddingConnectionStatus('failed');
        setEmbeddingConnectionError(result.message || '连接失败');
      }
    } catch (e: any) {
      setEmbeddingConnectionStatus('failed');
      setEmbeddingConnectionError(e.message || '网络错误');
    }
  };
  
  // 切换到向量化页面时测试连接并加载embedding提供者
  useEffect(() => {
    if (activeView === 'vectorize') {
      loadGlobalEmbeddingProviders();
      loadSettingsSections();
      if (activeEmbeddingProvider) {
        testEmbeddingConnection();
      }
    }
  }, [activeView, activeEmbeddingProvider]);
  
  const startVectorize = async () => {
    if (selectedForVectorize.size === 0) {
      alert('请选择要向量化的影片');
      return;
    }
    
    if (!activeEmbeddingProvider) {
      alert('请先在设置中配置Embedding模型');
      return;
    }

    try {
      // 解析选中项（支持剧集格式 douban_id_epN）
      const movieIds: string[] = [];
      const episodeItems: { douban_id: string; episode_number: number }[] = [];
      
      selectedForVectorize.forEach(id => {
        const epMatch = id.match(/^(.+)_ep(\d+)$/);
        if (epMatch) {
          episodeItems.push({
            douban_id: epMatch[1],
            episode_number: parseInt(epMatch[2])
          });
        } else {
          movieIds.push(id);
        }
      });
      
      setVectorizeQueueStatus({
        current: 0,
        total: selectedForVectorize.size,
        currentTitle: ''
      });
      
      const res = await fetch('http://127.0.0.1:8000/api/vectorize/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          movie_ids: movieIds,
          episode_items: episodeItems,
          provider_id: activeEmbeddingProvider
        })
      });

      if (res.ok) {
        // 清除之前的轮询
        if (vectorizePollRef.current) {
          clearInterval(vectorizePollRef.current);
        }
        
        vectorizePollRef.current = setInterval(async () => {
          try {
            const statusRes = await fetch('http://127.0.0.1:8000/api/vectorize/status');
            if (statusRes.ok) {
              const status = await statusRes.json();
              setVectorizeStatus(status);
              
              // 更新队列状态
              if (status.queue_progress) {
                setVectorizeQueueStatus({
                  current: status.queue_progress.current || 0,
                  total: status.queue_progress.total || selectedForVectorize.size,
                  currentTitle: status.current_movie || ''
                });
              }
              
              if (!status.running) {
                if (vectorizePollRef.current) {
                  clearInterval(vectorizePollRef.current);
                  vectorizePollRef.current = null;
                }
                setVectorizeStopping(false);
                await loadLibrary(true);
                setSelectedForVectorize(new Set());
              }
            }
          } catch (e) {
            console.error('获取向量化状态失败:', e);
          }
        }, 2000);
      } else {
        const error = await res.json();
        alert(error.detail || '启动向量化失败');
      }
    } catch (e) {
      console.error('向量化请求失败:', e);
      alert('向量化请求失败');
    }
  };
  
  const stopVectorize = async () => {
    if (!vectorizeStatus?.running) return;
    setVectorizeStopping(true);
    try {
      await fetch('http://127.0.0.1:8000/api/vectorize/cancel', { method: 'POST' });
    } catch (e) {
      console.error('取消向量化失败:', e);
    }
    if (vectorizePollRef.current) {
      clearInterval(vectorizePollRef.current);
      vectorizePollRef.current = null;
    }
    setVectorizeStatus((prev: any) => ({
      ...prev,
      running: false,
      current_movie: '已停止',
      error: '已取消'
    }));
    setVectorizeStopping(false);
    await loadLibrary(true);
    setSelectedForVectorize(new Set());
  };

  // ==================== 过滤与统计 ====================
  
  const filteredLibrary = libraryData.filter(movie => {
    if (searchTerm && !movie.title?.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    if (filterType === 'movie' && movie.media_type === 'tv') return false;
    if (filterType === 'tv' && movie.media_type !== 'tv') return false;
    if (filterType === 'no-subtitle' && movie.subtitle_path) return false;
    return true;
  });

  const stats = {
    total: libraryData.length,
    movies: libraryData.filter(m => m.media_type !== 'tv').length,
    tvShows: libraryData.filter(m => m.media_type === 'tv').length,
    annotated: libraryData.filter(m => m.status_annotate === 'done').length,
    vectorized: libraryData.filter(m => m.status_vectorize === 'done').length,
  };

  const handleDeleteEpisode = async (movie: Movie, episodeNumber: number) => {
    const confirmed = await requestConfirmation(
      `确定要从 "${movie.title}" 中删除第${episodeNumber}集吗？\n此操作不会删除原始文件。`,
      '删除剧集'
    );
    if (!confirmed) return;
    
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/library/delete-episode/${movie.douban_id}/${episodeNumber}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setLibraryLoading(true);
        loadLibrary(true);
      } else {
        alert('删除失败');
      }
    } catch (e) {
      console.error('删除失败:', e);
      alert('删除失败');
    }
  };

  // ==================== 渲染 ====================
  
  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      {/* 顶部标题栏 */}
      <header className="shrink-0 px-6 py-4 border-b border-white/5">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-white">影视资源管理</h1>
            <p className="text-xs text-gray-500 mt-0.5">管理您的影视库、导入新影片、进行语义标定</p>
          </div>
          <button 
            onClick={() => { setLibraryLoading(true); loadLibrary(true); refreshMovieList?.(); }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
          >
            <RefreshCw size={14} />
            刷新
          </button>
        </div>
      </header>

      {/* 导航标签 */}
      <nav className="shrink-0 px-6 py-3 border-b border-white/5 bg-[#0a0a0a]">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveView('library')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeView === 'library' 
                ? 'bg-blue-600 text-white' 
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Database size={16} />
            影片库
            <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">{stats.total}</span>
          </button>
          <button
            onClick={() => setActiveView('import')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeView === 'import' 
                ? 'bg-green-600 text-white' 
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <FolderInput size={16} />
            导入影片
          </button>
          <button
            onClick={() => setActiveView('annotate')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeView === 'annotate' 
                ? 'bg-indigo-600 text-white' 
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <FileSearch size={16} />
            语义标定
            {(() => {
              let pendingCount = 0;
              libraryData.forEach(m => {
                const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                if (isTv) {
                  // 电视剧：统计每一集未标定的
                  pendingCount += m.episodes!.filter(ep => ep.subtitle_path && !ep.annotation_path).length;
                } else if (m.subtitle_path && m.status_annotate !== 'done' && !m.annotation_path) {
                  // 电影：有字幕且未标定
                  pendingCount += 1;
                }
              });
              return pendingCount > 0 ? (
                <span className="text-xs bg-yellow-500 text-black px-1.5 py-0.5 rounded-full font-bold">
                  {pendingCount}
                </span>
              ) : null;
            })()}
            {stats.annotated > 0 && (() => {
              let pendingCount = 0;
              libraryData.forEach(m => {
                const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                if (isTv) {
                  pendingCount += m.episodes!.filter(ep => ep.subtitle_path && !ep.annotation_path).length;
                } else if (m.subtitle_path && m.status_annotate !== 'done' && !m.annotation_path) {
                  pendingCount += 1;
                }
              });
              return pendingCount === 0 ? (
                <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">{stats.annotated}</span>
              ) : null;
            })()}
          </button>
          <button
            onClick={() => setActiveView('vectorize')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeView === 'vectorize' 
                ? 'bg-purple-600 text-white' 
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Cpu size={16} />
            向量化入库
            {(() => {
              let pendingCount = 0;
              libraryData.forEach(m => {
                const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                if (isTv) {
                  // 电视剧：统计每一集已标定但未向量化的
                  pendingCount += m.episodes!.filter(ep => ep.annotation_path && !ep.vector_path).length;
                } else if ((m.status_annotate === 'done' || m.annotation_path) && m.status_vectorize !== 'done') {
                  // 电影：已标定但未向量化
                  pendingCount += 1;
                }
              });
              return pendingCount > 0 ? (
                <span className="text-xs bg-yellow-500 text-black px-1.5 py-0.5 rounded-full font-bold">
                  {pendingCount}
                </span>
              ) : null;
            })()}
            {stats.vectorized > 0 && (() => {
              let pendingCount = 0;
              libraryData.forEach(m => {
                const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                if (isTv) {
                  pendingCount += m.episodes!.filter(ep => ep.annotation_path && !ep.vector_path).length;
                } else if ((m.status_annotate === 'done' || m.annotation_path) && m.status_vectorize !== 'done') {
                  pendingCount += 1;
                }
              });
              return pendingCount === 0 ? (
                <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">{stats.vectorized}</span>
              ) : null;
            })()}
          </button>
        </div>
      </nav>

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden">
        
        {/* ========== 影片库视图 ========== */}
        {activeView === 'library' && (
          <div className="h-full flex flex-col">
            {/* 搜索筛选栏 */}
            <div className="shrink-0 px-6 py-3 border-b border-white/5 bg-[#111]">
              <div className="flex items-center gap-4">
                <div className="flex-1 max-w-sm relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input
                    type="text"
                    placeholder="搜索影片名..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 bg-[#1a1a1a] border border-white/10 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value as any)}
                  className="px-3 py-1.5 bg-[#1a1a1a] border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="all">全部类型</option>
                  <option value="movie">仅电影</option>
                  <option value="tv">仅电视剧</option>
                  <option value="no-subtitle">无字幕</option>
                </select>
                <div className="flex-1" />
                <div className="text-xs text-gray-500 space-x-4">
                  <span>电影: <span className="text-blue-400">{stats.movies}</span></span>
                  <span>电视剧: <span className="text-green-400">{stats.tvShows}</span></span>
                  <span>已标定: <span className="text-indigo-400">{stats.annotated}</span></span>
                  <span>已向量化: <span className="text-purple-400">{stats.vectorized}</span></span>
                </div>
              </div>
            </div>

            {/* 影片列表 */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
              {libraryLoading ? (
                <div className="h-full flex flex-col items-center justify-center text-gray-500">
                  <Loader2 size={48} className="mb-4 animate-spin opacity-40" />
                  <p className="text-sm">正在加载影片库...</p>
                </div>
              ) : filteredLibrary.length > 0 ? (
                <div className="grid grid-cols-1 gap-3">
                  {filteredLibrary.map((movie) => (
                    <LibraryMovieCard
                      key={movie.douban_id}
                      movie={movie}
                      onDeleteEpisode={handleDeleteEpisode}
                      onOpenFolder={handleOpenFolder}
                      onEditMovie={handleEditMovie}
                      onDeleteMovie={handleDeleteMovie}
                      onAnnotateEpisode={handleAnnotateEpisode}
                      onVectorizeEpisode={handleVectorizeEpisode}
                      onAnnotateMovie={handleAnnotateMovie}
                      onVectorizeMovie={handleVectorizeMovie}
                    />
                  ))}
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-gray-600">
                  <Database size={48} className="mb-4 opacity-20" />
                  <p className="text-lg">{libraryData.length === 0 ? '影片库为空' : '没有匹配的结果'}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    {libraryData.length === 0 ? '点击上方"导入影片"开始添加' : '尝试调整筛选条件'}
                  </p>
                  {libraryData.length === 0 && (
                    <button 
                      onClick={() => setActiveView('import')}
                      className="mt-4 flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg transition-colors"
                    >
                      <FolderInput size={16} />
                      导入影片
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========== 导入影片视图 ========== */}
        {activeView === 'import' && (
          <div className="h-full overflow-y-auto custom-scrollbar p-6">
            <div className="max-w-3xl mx-auto space-y-6">
              
              {/* 导入步骤说明 */}
              <div className="bg-[#151515] rounded-xl border border-white/5 p-6">
                <h3 className="font-bold text-white mb-4">导入流程</h3>
                <div className="flex items-center gap-4">
                  <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                    importStep === 'idle' ? 'bg-blue-500/20 text-blue-400' : 
                    'bg-green-500/20 text-green-400'
                  }`}>
                    <span className="w-6 h-6 rounded-full bg-current/20 flex items-center justify-center text-xs font-bold">1</span>
                    <span className="text-sm">选择文件夹</span>
                  </div>
                  <ChevronRight size={16} className="text-gray-600" />
                  <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                    importStep === 'scanning' ? 'bg-blue-500/20 text-blue-400' :
                    importStep === 'fetching' || importStep === 'done' ? 'bg-green-500/20 text-green-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    <span className="w-6 h-6 rounded-full bg-current/20 flex items-center justify-center text-xs font-bold">2</span>
                    <span className="text-sm">扫描影片</span>
                  </div>
                  <ChevronRight size={16} className="text-gray-600" />
                  <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                    importStep === 'fetching' ? 'bg-blue-500/20 text-blue-400 animate-pulse' :
                    importStep === 'done' ? 'bg-green-500/20 text-green-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    <span className="w-6 h-6 rounded-full bg-current/20 flex items-center justify-center text-xs font-bold">3</span>
                    <span className="text-sm">抓取元数据</span>
                  </div>
                  <ChevronRight size={16} className="text-gray-600" />
                  <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                    importStep === 'done' ? 'bg-green-500/20 text-green-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    <span className="w-6 h-6 rounded-full bg-current/20 flex items-center justify-center text-xs font-bold">4</span>
                    <span className="text-sm">完成</span>
                  </div>
                </div>

                {/* 进度条/状态提示 - 放在步骤条下方 */}
                {importStep === 'fetching' && (
                  <div className="mt-4 p-4 bg-blue-500/10 rounded-lg border border-blue-500/20">
                    <div className="flex items-center gap-2 mb-2">
                      <Loader2 size={14} className="animate-spin text-blue-400" />
                      <span className="text-sm text-white">正在抓取: {importProgress.currentItem}</span>
                    </div>
                    <ProgressBar 
                      progress={importProgress.current} 
                      total={importProgress.total} 
                    />
                  </div>
                )}

                {importStep === 'done' && (
                  <div className="mt-4 p-4 bg-green-500/10 rounded-lg border border-green-500/20">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 size={16} className="text-green-400" />
                      <span className="text-sm text-green-400">导入完成！共导入 {importProgress.total} 条记录</span>
                    </div>
                  </div>
                )}

                {importStep === 'error' && (
                  <div className="mt-4 p-4 bg-red-500/10 rounded-lg border border-red-500/20">
                    <div className="flex items-center gap-2">
                      <XCircle size={16} className="text-red-400" />
                      <span className="text-sm text-red-400">导入过程中出现错误</span>
                    </div>
                  </div>
                )}
              </div>

              {/* 选择文件夹 */}
              <div className="bg-[#151515] rounded-xl border border-white/5 p-6">
                <h3 className="font-bold text-white mb-2">选择媒体文件夹</h3>
                <p className="text-sm text-gray-500 mb-4">
                  选择包含影视文件的根目录，系统将自动扫描符合 "豆瓣ID-影片名" 格式的子文件夹
                </p>
                <div className="flex items-center gap-4">
                  <div className="flex-1 px-4 py-3 bg-[#1a1a1a] rounded-lg border border-white/10 font-mono text-sm text-gray-400 truncate">
                    {mediaPath || '未选择文件夹...'}
                  </div>
                  <button 
                    onClick={handleSelectAndScan}
                    disabled={importStep === 'fetching'}
                    className="shrink-0 flex items-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    <FolderOpen size={16} />
                    选择文件夹
                  </button>
                </div>
                
                {/* 操作按钮 - 放在文件夹选择下方 */}
                {(importStep === 'done' || importStep === 'error') && (
                  <div className="flex gap-3 mt-4">
                    <button
                      onClick={() => setActiveView('library')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors"
                    >
                      <Database size={16} />
                      查看影片库
                    </button>
                    <button
                      onClick={() => {
                        setImportStep('idle');
                        setScannedItems([]);
                        clearMovieList?.();
                      }}
                      className="flex items-center justify-center gap-2 px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors"
                    >
                      <RotateCcw size={16} />
                      重新导入
                    </button>
                  </div>
                )}
                
                {importStep === 'fetching' && canCancel && (
                  <div className="flex gap-3 mt-4">
                    <button
                      onClick={cancelImport}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-500 text-white font-medium rounded-lg transition-colors"
                    >
                      <X size={16} />
                      取消
                    </button>
                  </div>
                )}
              </div>

              {/* 扫描结果 */}
              {scannedItems.length > 0 && (
                <div className="bg-[#151515] rounded-xl border border-white/5 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold text-white">扫描结果</h3>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-gray-400">共 {scannedItems.length} 个</span>
                      <span className="text-green-400">{scannedItems.filter((i: any) => i._scan_status === 'new').length} 新增</span>
                      <span className="text-blue-400">{scannedItems.filter((i: any) => i._scan_status === 'updated').length} 更新</span>
                      <span className="text-gray-500">{scannedItems.filter((i: any) => i._scan_status === 'unchanged').length} 无变化</span>
                    </div>
                  </div>
                  
                  <div className="max-h-80 overflow-y-auto custom-scrollbar space-y-2">
                    {scannedItems.map((item: any, idx: number) => {
                      const isTV = item.media_type === 'tv' && item.episodes?.length > 0;
                      const isExpanded = expandedItems.has(item.douban_id);
                      const scanStatus = item._scan_status;
                      
                      return (
                        <div key={idx} className={`bg-[#1a1a1a] rounded-lg overflow-hidden ${scanStatus === 'unchanged' ? 'opacity-50' : ''}`}>
                          {/* 主条目 */}
                          <div 
                            className={`flex items-center gap-3 px-3 py-2 ${isTV ? 'cursor-pointer hover:bg-white/5' : ''}`}
                            onClick={() => {
                              if (isTV) {
                                setExpandedItems(prev => {
                                  const next = new Set(prev);
                                  if (next.has(item.douban_id)) {
                                    next.delete(item.douban_id);
                                  } else {
                                    next.add(item.douban_id);
                                  }
                                  return next;
                                });
                              }
                            }}
                          >
                            {isTV ? (
                              isExpanded ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />
                            ) : (
                              <Film size={14} className="text-gray-500" />
                            )}
                            <span className="text-sm text-white flex-1 truncate">{item.title || item.folder}</span>
                            {/* 状态标签 */}
                            {scanStatus === 'new' && (
                              <span className="text-xs text-green-400 bg-green-500/20 px-1.5 py-0.5 rounded">新增</span>
                            )}
                            {scanStatus === 'updated' && (
                              <span className="text-xs text-blue-400 bg-blue-500/20 px-1.5 py-0.5 rounded">更新</span>
                            )}
                            {isTV && (
                              <span className="text-xs text-blue-400 bg-blue-500/20 px-2 py-0.5 rounded">
                                {item.episodes?.length || item.video_count} 集
                              </span>
                            )}
                            <span className="text-xs text-gray-500">{item.douban_id}</span>
                            {item.subtitle_path ? (
                              <CheckCircle2 size={14} className="text-green-400" />
                            ) : (
                              <AlertTriangle size={14} className="text-yellow-400" />
                            )}
                          </div>
                          
                          {/* 电视剧集数列表 */}
                          {isTV && isExpanded && (
                            <div className="border-t border-white/5 bg-[#121212] px-3 py-2 space-y-1">
                              {item.episodes.map((ep: any) => (
                                <div key={ep.episode_number} className="flex items-center gap-2 text-xs text-gray-400 py-1">
                                  <span className="w-12 text-gray-500">第{ep.episode_number}集</span>
                                  <span className="flex-1 truncate">{ep.video_filename || ep.subtitle_filename || '-'}</span>
                                  <span title={ep.video_path ? "有视频" : "无视频"}>
                                    {ep.video_path ? (
                                      <CheckCircle2 size={12} className="text-green-400" />
                                    ) : (
                                      <XCircle size={12} className="text-orange-400" />
                                    )}
                                  </span>
                                  <span title={ep.subtitle_path ? "有字幕" : "无字幕"}>
                                    {ep.subtitle_path ? (
                                      <CheckCircle2 size={12} className="text-green-400" />
                                    ) : (
                                      <XCircle size={12} className="text-red-400" />
                                    )}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 说明 */}
              <div className="bg-[#151515] rounded-xl border border-white/5 p-6">
                <h3 className="font-bold text-white mb-3">文件夹命名规范</h3>
                <div className="space-y-2 text-sm text-gray-400">
                  <p>• 每个影视作品放在单独的文件夹中</p>
                  <p>• 文件夹命名格式：<code className="bg-white/10 px-1.5 py-0.5 rounded text-blue-400">豆瓣ID-影片名</code></p>
                  <p>• 示例：<code className="bg-white/10 px-1.5 py-0.5 rounded">25717233-心花路放</code></p>
                  <p>• 电视剧每集会生成独立的JSON文件，元数据只抓取一次</p>
                  <p>• 支持的视频格式：MP4, MKV, AVI, MOV, WMV, FLV, TS</p>
                  <p>• 支持的字幕格式：SRT, ASS, VTT</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========== 语义标定视图 ========== */}
        {activeView === 'annotate' && (
          <div className="h-full overflow-hidden flex flex-col">
            {/* 顶部统计栏 */}
            <div className="shrink-0 px-6 py-4 border-b border-white/5 bg-[#111]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <span className="text-sm text-gray-400">待标定</span>
                    <span className="text-lg font-bold text-yellow-400">
                      {(() => {
                        let count = 0;
                        libraryData.forEach(m => {
                          const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                          if (isTv) {
                            count += m.episodes!.filter(ep => ep.subtitle_path && !ep.annotation_path).length;
                          } else if (m.subtitle_path && m.status_annotate !== 'done' && !m.annotation_path) {
                            count += 1;
                          }
                        });
                        return count;
                      })()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-sm text-gray-400">已标定</span>
                    <span className="text-lg font-bold text-green-400">
                      {(() => {
                        let count = 0;
                        libraryData.forEach(m => {
                          const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                          if (isTv) {
                            count += m.episodes!.filter(ep => ep.subtitle_path && ep.annotation_path).length;
                          } else if (m.subtitle_path && (m.status_annotate === 'done' || m.annotation_path)) {
                            count += 1;
                          }
                        });
                        return count;
                      })()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    <span className="text-sm text-gray-400">仅视频</span>
                    <span className="text-lg font-bold text-orange-400">
                      {(() => {
                        let count = 0;
                        libraryData.forEach(m => {
                          const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                          if (isTv) {
                            count += m.episodes!.filter(ep => ep.video_path && !ep.subtitle_path).length;
                          } else if (m.video_path && !m.subtitle_path) {
                            count += 1;
                          }
                        });
                        return count;
                      })()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">已选 {selectedForAnnotation.size} 项</span>
                </div>
              </div>
            </div>

            {/* 主内容区 - 左右布局 */}
            <div className="flex-1 flex overflow-hidden">
              {/* 左侧：配置和操作 */}
              <div className="w-1/2 border-r border-white/5 flex flex-col overflow-y-auto custom-scrollbar">
                <div className="p-6 space-y-6">
                  {/* 开始按钮 */}
                  <button
                    onClick={startAnnotation}
                    disabled={annotationStatus?.running || selectedForAnnotation.size === 0 || !selectedProvider}
                    className="w-full flex items-center justify-center gap-2 px-4 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:from-gray-700 disabled:to-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all shadow-lg shadow-indigo-500/20 disabled:shadow-none"
                  >
                    {annotationStatus?.running ? (
                      <>
                        <Loader2 size={18} className="animate-spin" />
                        标注中...
                      </>
                    ) : (
                      <>
                        <Zap size={18} />
                        开始语义标定 ({selectedForAnnotation.size} 项)
                      </>
                    )}
                  </button>

                  {annotationStatus?.running && (
                    <button
                      onClick={stopAnnotation}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-medium rounded-xl transition-all shadow-lg shadow-red-500/20"
                    >
                      <X size={18} />
                      {annotationStopping ? '停止中（完成当前字幕后停止）' : '停止标定（完成当前字幕后停止）'}
                    </button>
                  )}

                  {/* 标定说明/进度（合并卡片） */}
                  <div className="bg-[#151515] rounded-xl border border-white/5 p-5">
                    {annotationStatus?.running ? (
                      <>
                        <div className="flex items-center gap-2 mb-3">
                          <Loader2 size={16} className="animate-spin text-indigo-400" />
                          <span className="text-sm font-medium text-white">语义标定进度</span>
                        </div>
                        <p className="text-sm text-gray-300 mb-3">
                          当前字幕：{annotationStatus.current_movie}
                          <span className="ml-2 text-xs text-gray-400">
                            已处理 {annotationStatus.progress || 0}/
                            {annotationStatus.total && annotationStatus.total > 0 ? annotationStatus.total : '…'} 条
                          </span>
                        </p>
                        <ProgressBar 
                          progress={annotationStatus.progress || 0} 
                          total={Math.max(annotationStatus.total || 0, annotationStatus.progress || 0, 1)}
                          color="purple"
                          label="当前字幕进度"
                        />
                        {annotationQueueStatus.total > 0 && (
                          <div className="mt-3">
                            <ProgressBar 
                              progress={annotationQueueStatus.current} 
                              total={annotationQueueStatus.total}
                              color="blue"
                              label={`任务进度（${annotationQueueStatus.current}/${annotationQueueStatus.total}）`}
                            />
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <h3 className="font-medium text-white mb-3">💡 标定说明</h3>
                        <div className="space-y-2 text-xs text-gray-400">
                          <p>• 分析每句台词的<span className="text-indigo-400">句型、情绪、语气</span>等语义特征</p>
                          <p>• 为每部影片生成结构化的标注JSON文件</p>
                          <p>• 电视剧会按集分别处理</p>
                          <p>• 标注结果用于后续语义搜索和智能混剪</p>
                        </div>
                      </>
                    )}
                  </div>

                  {/* AI模型选择 - 只读显示，与设置页同步 */}
                  <div className="bg-[#151515] rounded-xl border border-white/5 p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Cpu size={16} className="text-indigo-400" />
                        <h3 className="font-medium text-white">AI模型</h3>
                        <span className="text-xs text-gray-500">（在设置中配置）</span>
                      </div>
                      {/* 连接状态指示器 */}
                      <div className="flex items-center gap-2">
                        {llmConnectionStatus === 'testing' && (
                          <span className="flex items-center gap-1 text-xs text-gray-400">
                            <Loader2 size={12} className="animate-spin" />
                            测试中...
                          </span>
                        )}
                        {llmConnectionStatus === 'connected' && (
                          <span className="flex items-center gap-1 text-xs text-green-400">
                            <Check size={12} />
                            已连接
                          </span>
                        )}
                        {llmConnectionStatus === 'failed' && (
                          <span className="flex items-center gap-1 text-xs text-red-400" title={llmConnectionError}>
                            <X size={12} />
                            连接失败
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* 只读显示当前选中的模型 */}
                    {selectedProvider ? (
                      <div className="flex items-center gap-3 p-3 bg-[#1a1a1a] rounded-lg border border-white/10">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          llmProviders.find(p => p.id === selectedProvider)?.type === 'local' 
                            ? 'bg-green-500/20' 
                            : 'bg-purple-500/20'
                        }`}>
                          {llmProviders.find(p => p.id === selectedProvider)?.type === 'local' 
                            ? <Cpu size={20} className="text-green-400" />
                            : <Zap size={20} className="text-purple-400" />
                          }
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-white">
                            {llmProviders.find(p => p.id === selectedProvider)?.name || selectedProvider}
                          </p>
                          <p className="text-xs text-gray-500">
                            {llmProviders.find(p => p.id === selectedProvider)?.type === 'local' 
                              ? '本地模型 · 免费' 
                              : '商用API · 付费'
                            }
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                        <p className="text-sm text-yellow-400">
                          ⚠️ 未选择模型，请先在「设置 → 语义标定」中配置AI模型
                        </p>
                      </div>
                    )}
                    
                    {selectedProvider && (
                      <p className="mt-2 text-xs text-gray-500">
                        {llmProviders.find(p => p.id === selectedProvider)?.description}
                      </p>
                    )}
                    
                    {/* 连接错误详情 */}
                    {llmConnectionStatus === 'failed' && llmConnectionError && (
                      <p className="mt-2 text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">
                        {llmConnectionError}
                      </p>
                    )}
                  </div>

                  {/* 标注参数 - 只读显示，来自设置 */}
                  <div className="bg-[#151515] rounded-xl border border-white/5 p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Zap size={16} className="text-blue-400" />
                        <h3 className="font-medium text-white">标注参数</h3>
                        <span className="text-xs text-gray-500">（在设置中调整）</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex items-center justify-between p-2.5 bg-[#1a1a1a] rounded-lg">
                        <span className="text-xs text-gray-400">批处理大小</span>
                        <span className="text-xs text-blue-400 bg-blue-500/20 px-2 py-0.5 rounded">{annotationConfig.batch_size}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 bg-[#1a1a1a] rounded-lg">
                        <span className="text-xs text-gray-400">并发请求</span>
                        <span className="text-xs text-blue-400 bg-blue-500/20 px-2 py-0.5 rounded">{annotationConfig.concurrent_requests}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 bg-[#1a1a1a] rounded-lg">
                        <span className="text-xs text-gray-400">最大重试</span>
                        <span className="text-xs text-purple-400 bg-purple-500/20 px-2 py-0.5 rounded">{annotationConfig.max_retries}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 bg-[#1a1a1a] rounded-lg">
                        <span className="text-xs text-gray-400">保存间隔</span>
                        <span className="text-xs text-green-400 bg-green-500/20 px-2 py-0.5 rounded">{annotationConfig.save_interval} 条</span>
                      </div>
                    </div>
                  </div>

                  {/* API配置提示 - 简化版，引导到设置页面 */}
                  <div className="bg-gradient-to-r from-blue-500/10 to-indigo-500/10 rounded-xl border border-blue-500/20 p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                          <Cpu size={20} className="text-blue-400" />
                        </div>
                        <div>
                          <p className="text-sm text-white font-medium">需要配置 AI 模型？</p>
                          <p className="text-xs text-gray-400 mt-0.5">在设置中管理模型和 API Key</p>
                        </div>
                      </div>
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          // 触发设置面板打开 - 通过自定义事件
                          window.dispatchEvent(new CustomEvent('openSettings', { detail: { tab: 'llm' } }));
                        }}
                        className="flex items-center gap-1.5 px-3 py-2 text-sm text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 rounded-lg transition-colors"
                      >
                        前往设置
                        <ChevronRight size={14} />
                      </a>
                    </div>
                  </div>

                </div>
              </div>

              {/* 右侧：影片选择列表 */}
              <div className="w-1/2 flex flex-col">
                <div className="shrink-0 px-4 py-3 border-b border-white/5 bg-[#0d0d0d]">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-white">选择要标定的影片</h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          if (selectedForAnnotation.size > 0) {
                            setSelectedForAnnotation(new Set());
                          } else {
                            // 收集所有待标定项（电影用 douban_id，电视剧剧集用 douban_id_epN）
                            const pendingIds: string[] = [];
                            libraryData.forEach(m => {
                              const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                              if (isTv) {
                                // 电视剧：收集有字幕且未标定的剧集
                                m.episodes?.forEach(ep => {
                                  if (ep.subtitle_path && !ep.annotation_path) {
                                    pendingIds.push(`${m.douban_id}_ep${ep.episode_number}`);
                                  }
                                });
                              } else {
                                // 电影：有字幕且未标定
                                if (m.subtitle_path && m.status_annotate !== 'done' && !m.annotation_path) {
                                  pendingIds.push(m.douban_id);
                                }
                              }
                            });
                            setSelectedForAnnotation(new Set(pendingIds));
                          }
                        }}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        {selectedForAnnotation.size > 0 ? '取消全选' : '全选待标定'}
                      </button>
                    </div>
                  </div>
                </div>
                
                <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
                  {libraryData.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <Film size={40} className="mb-3 opacity-30" />
                      <p className="text-sm">暂无可标定的影片</p>
                      <p className="text-xs mt-1">请先导入影片</p>
                    </div>
                  ) : (
                    libraryData.map(movie => {
                      const isTv = movie.media_type === 'tv' && movie.episodes && movie.episodes.length > 0;
                      const movieHasSubtitle = Boolean(movie.subtitle_path);
                      const movieHasOnlyVideo = Boolean(movie.video_path) && !movieHasSubtitle;
                      const isMovieAnnotated = movie.status_annotate === 'done' || Boolean(movie.annotation_path);
                      
                      // 电视剧：展开显示所有剧集
                      if (isTv) {
                        const episodes = movie.episodes || [];
                        const hasAnySubtitle = episodes.some(ep => ep.subtitle_path);
                        const hasAnyVideo = episodes.some(ep => ep.video_path);
                        
                        // 如果没有任何字幕和视频，则不显示该剧集
                        if (!hasAnySubtitle && !hasAnyVideo) return null;
                        
                        return (
                          <div key={movie.douban_id} className="bg-[#1a1a1a] rounded-lg border border-white/5 overflow-hidden">
                            {/* 剧集标题栏 */}
                            <div className="flex items-center gap-3 p-3 border-b border-white/5 bg-[#151515]">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-white truncate">{movie.title}</span>
                                  <span className="text-[10px] text-blue-400 bg-blue-500/20 px-1.5 py-0.5 rounded">剧集</span>
                                  <span className="text-[10px] text-gray-500">{episodes.length} 集</span>
                                </div>
                                {movie.director && (
                                  <p className="text-xs text-gray-500 truncate mt-0.5">{movie.director}</p>
                                )}
                              </div>
                            </div>
                            {/* 剧集列表 */}
                            <div className="divide-y divide-white/5">
                              {episodes.map((ep) => {
                                const epHasSubtitle = Boolean(ep.subtitle_path);
                                const epHasOnlyVideo = Boolean(ep.video_path) && !epHasSubtitle;
                                const epIsAnnotated = Boolean(ep.annotation_path);
                                const epKey = `${movie.douban_id}_ep${ep.episode_number}`;
                                // 已标定的不可选择
                                const canSelect = epHasSubtitle && !epIsAnnotated;
                                
                                // 如果既没有字幕也没有视频，跳过
                                if (!ep.subtitle_path && !ep.video_path) return null;
                                
                                return (
                                  <label 
                                    key={ep.episode_number}
                                    className={`flex items-center gap-3 px-4 py-2.5 transition-all ${
                                      canSelect ? 'cursor-pointer hover:bg-white/5' : 'cursor-not-allowed opacity-60'
                                    } ${
                                      selectedForAnnotation.has(epKey) 
                                        ? 'bg-indigo-500/15' 
                                        : ''
                                    } ${
                                      epIsAnnotated ? 'bg-green-500/5' : ''
                                    }`}
                                  >
                                    <input
                                      type="checkbox"
                                      checked={selectedForAnnotation.has(epKey)}
                                      disabled={!canSelect}
                                      onChange={() => {
                                        if (!canSelect) return;
                                        const newSet = new Set(selectedForAnnotation);
                                        if (newSet.has(epKey)) {
                                          newSet.delete(epKey);
                                        } else {
                                          newSet.add(epKey);
                                        }
                                        setSelectedForAnnotation(newSet);
                                      }}
                                      className="w-4 h-4 rounded accent-indigo-500 disabled:opacity-40"
                                    />
                                    <span className="w-16 text-xs text-gray-400 shrink-0">第{ep.episode_number}集</span>
                                    <span className="flex-1 text-xs text-gray-500 truncate" title={ep.subtitle_filename || ep.video_filename || ''}>
                                      {ep.subtitle_filename || ep.subtitle_path?.split(/[/\\]/).pop() || ep.video_filename || ep.video_path?.split(/[/\\]/).pop() || '-'}
                                    </span>
                                    {epHasOnlyVideo && (
                                      <span className="flex items-center gap-1 text-xs text-orange-400 bg-orange-500/10 px-2 py-1 rounded">
                                        <XCircle size={10} />
                                        仅视频
                                      </span>
                                    )}
                                    {epHasSubtitle && epIsAnnotated && (
                                      <span className="flex items-center gap-1 text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded">
                                        <CheckCircle2 size={10} />
                                        已标定
                                      </span>
                                    )}
                                    {epHasSubtitle && !epIsAnnotated && (
                                      <span className="flex items-center gap-1 text-xs text-yellow-400 bg-yellow-500/10 px-2 py-1 rounded">
                                        <AlertTriangle size={10} />
                                        待标定
                                      </span>
                                    )}
                                  </label>
                                );
                              })}
                            </div>
                          </div>
                        );
                      }
                      
                      // 电影：单行显示
                      // 如果既没有字幕也没有视频，跳过
                      if (!movieHasSubtitle && !movie.video_path) return null;
                      
                      // 已标定的电影不可选择
                      const canSelect = movieHasSubtitle && !isMovieAnnotated;
                      
                      return (
                        <label 
                          key={movie.douban_id}
                          className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                            canSelect ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'
                          } ${
                            selectedForAnnotation.has(movie.douban_id) 
                              ? 'bg-indigo-500/20 border border-indigo-500/40 shadow-lg shadow-indigo-500/10' 
                              : isMovieAnnotated
                                ? 'bg-green-500/5 border border-green-500/20'
                                : 'bg-[#1a1a1a] border border-transparent hover:border-white/10 hover:bg-[#1f1f1f]'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedForAnnotation.has(movie.douban_id)}
                            disabled={!canSelect}
                            onChange={() => {
                              if (!canSelect) return;
                              const newSet = new Set(selectedForAnnotation);
                              if (newSet.has(movie.douban_id)) {
                                newSet.delete(movie.douban_id);
                              } else {
                                newSet.add(movie.douban_id);
                              }
                              setSelectedForAnnotation(newSet);
                            }}
                            className="w-4 h-4 rounded accent-indigo-500 disabled:opacity-40"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-white truncate">{movie.title}</span>
                            </div>
                            {movie.director && (
                              <p className="text-xs text-gray-500 truncate mt-0.5">{movie.director}</p>
                            )}
                          </div>
                          {movieHasOnlyVideo && (
                            <span className="flex items-center gap-1 text-xs text-orange-400 bg-orange-500/10 px-2 py-1 rounded">
                              <XCircle size={10} />
                              仅视频
                            </span>
                          )}
                          {movieHasSubtitle && isMovieAnnotated && (
                            <span className="flex items-center gap-1 text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded">
                              <CheckCircle2 size={12} />
                              已标定
                            </span>
                          )}
                          {movieHasSubtitle && !isMovieAnnotated && (
                            <span className="flex items-center gap-1 text-xs text-yellow-400 bg-yellow-500/10 px-2 py-1 rounded">
                              <AlertTriangle size={12} />
                              待标定
                            </span>
                          )}
                        </label>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========== 向量化入库视图 ========== */}
        {activeView === 'vectorize' && (
          <div className="h-full overflow-hidden flex flex-col">
            {/* 顶部统计栏 */}
            <div className="shrink-0 px-6 py-4 border-b border-white/5 bg-[#111]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <span className="text-sm text-gray-400">待入库</span>
                    <span className="text-lg font-bold text-yellow-400">
                      {(() => {
                        let count = 0;
                        libraryData.forEach(m => {
                          const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                          if (isTv) {
                            count += m.episodes!.filter(ep => ep.annotation_path && !ep.vector_path).length;
                          } else if ((m.status_annotate === 'done' || m.annotation_path) && m.status_vectorize !== 'done') {
                            count += 1;
                          }
                        });
                        return count;
                      })()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-sm text-gray-400">已入库</span>
                    <span className="text-lg font-bold text-green-400">
                      {(() => {
                        let count = 0;
                        libraryData.forEach(m => {
                          const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                          if (isTv) {
                            count += m.episodes!.filter(ep => ep.annotation_path && ep.vector_path).length;
                          } else if (m.status_vectorize === 'done') {
                            count += 1;
                          }
                        });
                        return count;
                      })()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-indigo-500"></div>
                    <span className="text-sm text-gray-400">已标定</span>
                    <span className="text-lg font-bold text-indigo-400">{stats.annotated}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">已选 {selectedForVectorize.size} 项</span>
                </div>
              </div>
            </div>

            {/* 主内容区 - 左右布局（与语义标定一致：左配置右列表） */}
            <div className="flex-1 flex overflow-hidden">
              {/* 左侧：配置和操作 */}
              <div className="w-1/2 border-r border-white/5 flex flex-col overflow-y-auto custom-scrollbar">
                <div className="p-6 space-y-6">
                  {/* 开始按钮 */}
                  <button
                    onClick={startVectorize}
                    disabled={vectorizeStatus?.running || selectedForVectorize.size === 0 || !embeddingProvider}
                    className="w-full flex items-center justify-center gap-2 px-4 py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:from-gray-700 disabled:to-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all shadow-lg shadow-purple-500/20 disabled:shadow-none"
                  >
                    {vectorizeStatus?.running ? (
                      <>
                        <Loader2 size={18} className="animate-spin" />
                        向量化中...
                      </>
                    ) : (
                      <>
                        <Zap size={18} />
                        开始向量化入库 ({selectedForVectorize.size} 项)
                      </>
                    )}
                  </button>

                  {vectorizeStatus?.running && (
                    <button
                      onClick={stopVectorize}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-medium rounded-xl transition-all shadow-lg shadow-red-500/20"
                    >
                      <X size={18} />
                      {vectorizeStopping ? '停止中（完成当前批次后停止）' : '停止向量化（完成当前批次后停止）'}
                    </button>
                  )}

                  {/* 向量化说明/进度（合并卡片） */}
                  <div className="bg-[#151515] rounded-xl border border-white/5 p-5">
                    {vectorizeStatus?.running ? (
                      <>
                        <div className="flex items-center gap-2 mb-3">
                          <Loader2 size={16} className="animate-spin text-purple-400" />
                          <span className="text-sm font-medium text-white">向量化进度</span>
                        </div>
                        <p className="text-sm text-gray-300 mb-3">
                          当前影片：{vectorizeStatus.current_movie || '准备中...'}
                          <span className="ml-2 text-xs text-gray-400">
                            已处理 {vectorizeStatus.progress || 0}/
                            {vectorizeStatus.total && vectorizeStatus.total > 0 ? vectorizeStatus.total : '…'} 条
                          </span>
                        </p>
                        <ProgressBar 
                          progress={vectorizeStatus.progress || 0} 
                          total={Math.max(vectorizeStatus.total || 0, vectorizeStatus.progress || 0, 1)}
                          color="purple"
                          label="当前影片进度"
                        />
                        {vectorizeQueueStatus.total > 0 && (
                          <div className="mt-3">
                            <ProgressBar 
                              progress={vectorizeQueueStatus.current} 
                              total={vectorizeQueueStatus.total}
                              color="pink"
                              label={`任务进度（${vectorizeQueueStatus.current}/${vectorizeQueueStatus.total}）`}
                            />
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <h3 className="font-medium text-white mb-3">💡 向量化说明</h3>
                        <div className="space-y-2 text-xs text-gray-400">
                          <p>• 采用<span className="text-purple-400">单句向量化</span>策略，每句台词生成一个向量</p>
                          <p>• 向量包含：台词内容 + 句型 + 情绪 + 语气</p>
                          <p>• 入库后支持：语义搜索、智能接话、情绪筛选</p>
                          <p>• 电视剧会按集分别处理</p>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Embedding模型选择 - 只读显示，与设置页同步 */}
                  <div className="bg-[#151515] rounded-xl border border-white/5 p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Cpu size={16} className="text-purple-400" />
                        <h3 className="font-medium text-white">Embedding模型</h3>
                        <span className="text-xs text-gray-500">（在设置中配置）</span>
                      </div>
                      {/* 连接状态指示器 */}
                      <div className="flex items-center gap-2">
                        {embeddingConnectionStatus === 'testing' && (
                          <span className="flex items-center gap-1 text-xs text-gray-400">
                            <Loader2 size={12} className="animate-spin" />
                            测试中...
                          </span>
                        )}
                        {embeddingConnectionStatus === 'connected' && (
                          <span className="flex items-center gap-1 text-xs text-green-400">
                            <Check size={12} />
                            已连接
                          </span>
                        )}
                        {embeddingConnectionStatus === 'failed' && (
                          <span className="flex items-center gap-1 text-xs text-red-400" title={embeddingConnectionError}>
                            <X size={12} />
                            连接失败
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* 只读显示当前选中的模型 */}
                    {embeddingProvider ? (
                      <div className="flex items-center gap-3 p-3 bg-[#1a1a1a] rounded-lg border border-white/10">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          embeddingProvider.type === 'local' 
                            ? 'bg-green-500/20' 
                            : 'bg-purple-500/20'
                        }`}>
                          {embeddingProvider.type === 'local' 
                            ? <HardDrive size={20} className="text-green-400" />
                            : <Zap size={20} className="text-purple-400" />
                          }
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-white">
                            {embeddingProvider.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {embeddingProvider.type === 'local' 
                              ? '本地模型 · 免费' 
                              : '商用API · 付费'
                            }
                            {embeddingProvider.dimension && ` · ${embeddingProvider.dimension}维`}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                        <p className="text-sm text-yellow-400">
                          ⚠️ 未选择模型，请先在「设置 → 向量化入库」中配置Embedding模型
                        </p>
                      </div>
                    )}
                    
                    {embeddingProvider && (
                      <p className="mt-2 text-xs text-gray-500">
                        {embeddingProvider.description}
                      </p>
                    )}
                    
                    {/* 连接错误详情 */}
                    {embeddingConnectionStatus === 'failed' && embeddingConnectionError && (
                      <p className="mt-2 text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">
                        {embeddingConnectionError}
                      </p>
                    )}
                  </div>

                  {/* 向量化参数 - 只读显示，来自设置 */}
                  <div className="bg-[#151515] rounded-xl border border-white/5 p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Zap size={16} className="text-pink-400" />
                        <h3 className="font-medium text-white">向量化参数</h3>
                        <span className="text-xs text-gray-500">（在设置中调整）</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex items-center justify-between p-2.5 bg-[#1a1a1a] rounded-lg">
                        <span className="text-xs text-gray-400">批处理大小</span>
                        <span className="text-xs text-purple-400 bg-purple-500/20 px-2 py-0.5 rounded">{vectorizationConfig.batch_size}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 bg-[#1a1a1a] rounded-lg">
                        <span className="text-xs text-gray-400">并发请求</span>
                        <span className="text-xs text-purple-400 bg-purple-500/20 px-2 py-0.5 rounded">{vectorizationConfig.concurrent_requests}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 bg-[#1a1a1a] rounded-lg">
                        <span className="text-xs text-gray-400">最大重试</span>
                        <span className="text-xs text-pink-400 bg-pink-500/20 px-2 py-0.5 rounded">{vectorizationConfig.max_retries}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 bg-[#1a1a1a] rounded-lg">
                        <span className="text-xs text-gray-400">重试延迟</span>
                        <span className="text-xs text-green-400 bg-green-500/20 px-2 py-0.5 rounded">{vectorizationConfig.retry_delay}ms</span>
                      </div>
                    </div>
                  </div>

                  {/* 向量库配置 */}
                  <div className="bg-[#151515] rounded-xl border border-white/5 p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <Database size={16} className="text-purple-400" />
                      <h3 className="font-medium text-white">向量库配置</h3>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 bg-[#1a1a1a] rounded-lg">
                        <div className="text-xs text-gray-500 mb-1">数据库</div>
                        <div className="text-sm font-medium text-white">ChromaDB</div>
                      </div>
                      <div className="p-3 bg-[#1a1a1a] rounded-lg">
                        <div className="text-xs text-gray-500 mb-1">向量维度</div>
                        <div className="text-sm font-medium text-white">{embeddingProvider?.dimension || 2560}</div>
                      </div>
                    </div>
                    
                    <div className="mt-3">
                      <div className="text-xs text-gray-500 mb-1">存储路径</div>
                      <code className="block text-xs bg-black/30 text-purple-400 px-3 py-2 rounded-lg">
                        data/chroma_db/
                      </code>
                    </div>
                  </div>

                  {/* API配置提示 - 简化版，引导到设置页面 */}
                  <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-xl border border-purple-500/20 p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
                          <HardDrive size={20} className="text-purple-400" />
                        </div>
                        <div>
                          <p className="text-sm text-white font-medium">需要配置 Embedding 模型？</p>
                          <p className="text-xs text-gray-400 mt-0.5">在设置中管理模型配置</p>
                        </div>
                      </div>
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          window.dispatchEvent(new CustomEvent('openSettings', { detail: { tab: 'embedding' } }));
                        }}
                        className="flex items-center gap-1.5 px-3 py-2 text-sm text-purple-400 hover:text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 rounded-lg transition-colors"
                      >
                        前往设置
                        <ChevronRight size={14} />
                      </a>
                    </div>
                  </div>

                </div>
              </div>

              {/* 右侧：影片选择列表 */}
              <div className="w-1/2 flex flex-col">
                <div className="shrink-0 px-4 py-3 border-b border-white/5 bg-[#0d0d0d]">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-white">选择要向量化的影片</h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          if (selectedForVectorize.size > 0) {
                            setSelectedForVectorize(new Set());
                          } else {
                            // 收集所有待入库项（电影用 douban_id，电视剧剧集用 douban_id_epN）
                            const pendingIds: string[] = [];
                            libraryData.forEach(m => {
                              const isTv = m.media_type === 'tv' && m.episodes && m.episodes.length > 0;
                              if (isTv) {
                                // 电视剧：收集有标注但未向量化的剧集
                                m.episodes?.forEach(ep => {
                                  if (ep.annotation_path && !ep.vector_path) {
                                    pendingIds.push(`${m.douban_id}_ep${ep.episode_number}`);
                                  }
                                });
                              } else {
                                // 电影：已标定但未向量化
                                if ((m.status_annotate === 'done' || m.annotation_path) && m.status_vectorize !== 'done') {
                                  pendingIds.push(m.douban_id);
                                }
                              }
                            });
                            setSelectedForVectorize(new Set(pendingIds));
                          }
                        }}
                        className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
                      >
                        {selectedForVectorize.size > 0 ? '取消全选' : '全选待入库'}
                      </button>
                    </div>
                  </div>
                </div>
                
                <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
                  {libraryData.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <Film size={40} className="mb-3 opacity-30" />
                      <p className="text-sm">暂无可向量化的影片</p>
                      <p className="text-xs mt-1">请先导入影片并完成语义标定</p>
                    </div>
                  ) : libraryData.filter(m => m.status_annotate === 'done' || m.annotation_path || (m.episodes && m.episodes.some(ep => ep.annotation_path))).length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <FileSearch size={40} className="mb-3 opacity-30" />
                      <p className="text-sm">暂无已标定的影片</p>
                      <button 
                        onClick={() => setActiveView('annotate')}
                        className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 px-3 py-1.5 rounded-lg"
                      >
                        去进行语义标定 →
                      </button>
                    </div>
                  ) : (
                    libraryData.map(movie => {
                      const isTv = movie.media_type === 'tv' && movie.episodes && movie.episodes.length > 0;
                      const movieHasAnnotation = Boolean(movie.annotation_path) || movie.status_annotate === 'done';
                      const isMovieVectorized = movie.status_vectorize === 'done';
                      
                      // 电视剧：展开显示所有剧集
                      if (isTv) {
                        const episodes = movie.episodes || [];
                        const hasAnyAnnotation = episodes.some(ep => ep.annotation_path);
                        
                        // 如果没有任何标注，则不显示该剧集
                        if (!hasAnyAnnotation) return null;
                        
                        return (
                          <div key={movie.douban_id} className="bg-[#1a1a1a] rounded-lg border border-white/5 overflow-hidden">
                            {/* 剧集标题栏 */}
                            <div className="flex items-center gap-3 p-3 border-b border-white/5 bg-[#151515]">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-white truncate">{movie.title}</span>
                                  <span className="text-[10px] text-blue-400 bg-blue-500/20 px-1.5 py-0.5 rounded">剧集</span>
                                  <span className="text-[10px] text-gray-500">{episodes.length} 集</span>
                                </div>
                              </div>
                              <button
                                onClick={() => {
                                  // 全选/取消该剧集的所有待入库剧集
                                  const pendingEpisodeIds = episodes
                                    .filter(ep => ep.annotation_path && !ep.vector_path)
                                    .map(ep => `${movie.douban_id}_ep${ep.episode_number}`);
                                  
                                  const allSelected = pendingEpisodeIds.every(id => selectedForVectorize.has(id));
                                  const newSet = new Set(selectedForVectorize);
                                  
                                  if (allSelected) {
                                    pendingEpisodeIds.forEach(id => newSet.delete(id));
                                  } else {
                                    pendingEpisodeIds.forEach(id => newSet.add(id));
                                  }
                                  setSelectedForVectorize(newSet);
                                }}
                                className="text-[10px] text-purple-400 hover:text-purple-300"
                              >
                                {episodes.filter(ep => ep.annotation_path && !ep.vector_path).every(ep => 
                                  selectedForVectorize.has(`${movie.douban_id}_ep${ep.episode_number}`)
                                ) ? '取消全选' : '全选待入库'}
                              </button>
                            </div>
                            
                            {/* 剧集列表 */}
                            <div className="divide-y divide-white/5">
                              {episodes.filter(ep => ep.annotation_path).map(ep => {
                                const epKey = `${movie.douban_id}_ep${ep.episode_number}`;
                                const isVectorized = Boolean(ep.vector_path);
                                
                                return (
                                  <label
                                    key={epKey}
                                    className={`flex items-center gap-3 px-3 py-2 cursor-pointer transition-all ${
                                      selectedForVectorize.has(epKey)
                                        ? 'bg-purple-500/10'
                                        : 'hover:bg-white/5'
                                    }`}
                                  >
                                    <input
                                      type="checkbox"
                                      checked={selectedForVectorize.has(epKey)}
                                      onChange={() => {
                                        const newSet = new Set(selectedForVectorize);
                                        if (newSet.has(epKey)) {
                                          newSet.delete(epKey);
                                        } else {
                                          newSet.add(epKey);
                                        }
                                        setSelectedForVectorize(newSet);
                                      }}
                                      className="w-3.5 h-3.5 rounded accent-purple-500"
                                    />
                                    <span className="text-xs text-gray-400 w-12">第{ep.episode_number}集</span>
                                    <span className="flex-1 text-xs text-gray-300 truncate">
                                      {ep.subtitle_filename || ep.video_filename || '-'}
                                    </span>
                                    {isVectorized ? (
                                      <span className="flex items-center gap-1 text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded">
                                        <CheckCircle2 size={10} />
                                        已入库
                                      </span>
                                    ) : (
                                      <span className="flex items-center gap-1 text-[10px] text-yellow-400 bg-yellow-500/10 px-1.5 py-0.5 rounded">
                                        <Database size={10} />
                                        待入库
                                      </span>
                                    )}
                                  </label>
                                );
                              })}
                            </div>
                          </div>
                        );
                      }
                      
                      // 电影：只显示已标定的
                      if (!movieHasAnnotation) return null;
                      
                      return (
                        <label 
                          key={movie.douban_id}
                          className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                            selectedForVectorize.has(movie.douban_id) 
                              ? 'bg-purple-500/20 border border-purple-500/40 shadow-lg shadow-purple-500/10' 
                              : 'bg-[#1a1a1a] border border-transparent hover:border-white/10 hover:bg-[#1f1f1f]'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedForVectorize.has(movie.douban_id)}
                            onChange={() => {
                              const newSet = new Set(selectedForVectorize);
                              if (newSet.has(movie.douban_id)) {
                                newSet.delete(movie.douban_id);
                              } else {
                                newSet.add(movie.douban_id);
                              }
                              setSelectedForVectorize(newSet);
                            }}
                            className="w-4 h-4 rounded accent-purple-500"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-white truncate">{movie.title}</span>
                            </div>
                            {movie.director && (
                              <p className="text-xs text-gray-500 truncate mt-0.5">{movie.director}</p>
                            )}
                          </div>
                          {isMovieVectorized ? (
                            <span className="flex items-center gap-1 text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded">
                              <CheckCircle2 size={12} />
                              已入库
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-xs text-yellow-400 bg-yellow-500/10 px-2 py-1 rounded">
                              <Database size={12} />
                              待入库
                            </span>
                          )}
                        </label>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      {editingMovie && (
        <EditMovieModal
          movie={editingMovie}
          form={editForm}
          onChange={(key, value) => setEditForm((prev) => ({ ...prev, [key]: value }))}
          onClose={closeEditModal}
          onSubmit={handleSaveEdit}
          saving={savingEdit}
        />
      )}
    </div>
  );
}