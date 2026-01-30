// src/store/videoStore.ts
import { create } from 'zustand';
import { getVideoThumbnail, releaseThumbnail } from '@/utils/videoUtils';

// LRU缓存配置 (10个视频缩略图)
const MAX_CACHE_SIZE = 10;

interface ThumbnailCache {
  [videoPath: string]: {
    url: string;
    lastAccessed: number;
    refCount: number; // 引用计数 (防止误删)
  };
}

interface VideoStore {
  thumbnailCache: ThumbnailCache;
  
  // 核心方法
  getThumbnail: (videoPath: string) => Promise<string>;
  incrementRef: (videoPath: string) => void;
  decrementRef: (videoPath: string) => void;
  clearCache: () => void;
  
  // 内存优化
  evictOldest: () => void;
}

export const useVideoStore = create<VideoStore>((set, get) => ({
  thumbnailCache: {},
  
  // 获取缩略图 (带缓存)
  getThumbnail: async (videoPath: string) => {
    const cache = get().thumbnailCache;
    
    // 命中缓存
    if (cache[videoPath]) {
      cache[videoPath].lastAccessed = Date.now();
      cache[videoPath].refCount += 1;
      set({ thumbnailCache: { ...cache } });
      return cache[videoPath].url;
    }
    
    // 生成新缩略图
    const url = await getVideoThumbnail(videoPath);
    
    // LRU缓存管理
    const newCache = { ...cache, [videoPath]: { url, lastAccessed: Date.now(), refCount: 1 } };
    
    // 超过缓存上限时清理
    if (Object.keys(newCache).length > MAX_CACHE_SIZE) {
      // 按访问时间排序
      const sorted = Object.entries(newCache)
        .sort((a, b) => a[1].lastAccessed - b[1].lastAccessed);
      
      // 释放最旧且无引用的缩略图
      for (const [path, item] of sorted) {
        if (item.refCount === 0) {
          releaseThumbnail(item.url);
          delete newCache[path];
          break;
        }
      }
    }
    
    set({ thumbnailCache: newCache });
    return url;
  },
  
  // 增加引用计数 (节点使用时调用)
  incrementRef: (videoPath: string) => {
    const cache = get().thumbnailCache;
    if (cache[videoPath]) {
      cache[videoPath].refCount += 1;
      set({ thumbnailCache: { ...cache } });
    }
  },
  
  // 减少引用计数 (节点销毁时调用)
  decrementRef: (videoPath: string) => {
    const cache = get().thumbnailCache;
    if (cache[videoPath]) {
      cache[videoPath].refCount = Math.max(0, cache[videoPath].refCount - 1);
      set({ thumbnailCache: { ...cache } });
    }
  },
  
  // 清空缓存 (释放所有资源)
  clearCache: () => {
    const cache = get().thumbnailCache;
    Object.values(cache).forEach(item => releaseThumbnail(item.url));
    set({ thumbnailCache: {} });
  },
  
  // 手动触发LRU清理
  evictOldest: () => {
    const cache = get().thumbnailCache;
    const sorted = Object.entries(cache)
      .sort((a, b) => a[1].lastAccessed - b[1].lastAccessed);
    
    if (sorted.length > 0) {
      const [oldestPath, oldestItem] = sorted[0];
      if (oldestItem.refCount === 0) {
        releaseThumbnail(oldestItem.url);
        const newCache = { ...cache };
        delete newCache[oldestPath];
        set({ thumbnailCache: newCache });
      }
    }
  }
}));

// 组件卸载时自动清理缩略图
export const useThumbnailCleanup = (videoPath: string | null) => {
  const { incrementRef, decrementRef } = useVideoStore();
  
  React.useEffect(() => {
    if (videoPath) {
      incrementRef(videoPath);
      return () => decrementRef(videoPath);
    }
  }, [videoPath, incrementRef, decrementRef]);
};