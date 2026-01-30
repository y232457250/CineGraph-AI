// src/utils/videoUtils.ts
import { invoke } from '@tauri-apps/api/core';

/**
 * 获取媒体文件列表 (通过Tauri安全API)
 * 避免前端直接访问文件系统 (安全限制)
 */
export interface MediaFile {
  path: string;
  name: string;
  type: 'video' | 'subtitle' | 'directory';
  size?: number;
  modified?: string;
}

export const getMediaFiles = async (basePath: string = 'data/media'): Promise<MediaFile[]> => {
  try {
    // 使用Tauri invoke调用Rust后端 (安全)
    const files: MediaFile[] = await invoke('list_media_files', { 
      basePath: basePath.replace(/\\/g, '/') // Windows路径标准化
    });
    
    // 过滤无效文件
    return files.filter(file => 
      (file.type === 'video' && /\.(mp4|mkv|avi)$/i.test(file.name)) ||
      (file.type === 'subtitle' && /\.(srt|ass|vtt)$/i.test(file.name))
    );
  } catch (error) {
    console.error('获取媒体文件失败:', error);
    return [];
  }
};

/**
 * 获取视频缩略图 (调用FastAPI后端)
 * 避免前端加载完整视频 (内存优化)
 */
export const getVideoThumbnail = async (videoPath: string): Promise<string> => {
  try {
    // 标准化Windows路径 (D:\AI\... → D:/AI/...)
    const normalizedPath = videoPath.replace(/\\/g, '/');
    
    // 调用FastAPI后端生成缩略图
    const response = await fetch(`http://localhost:8000/api/video/thumbnail?path=${encodeURIComponent(normalizedPath)}`);
    
    if (!response.ok) throw new Error('缩略图生成失败');
    
    // 转换为ObjectURL (避免Base64内存泄漏)
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch (error) {
    console.error('缩略图加载失败:', error);
    // 返回默认占位图
    return 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iNTYiIHZpZXdCb3g9IjAgMCAxMDAgNTYiPjxwYXRoIGZpbGw9IiMzYTNhNGEiIGQ9Ik0wIDBoMTAwdjU2SDB6Ii8+PHRleHQgeD0iNTAiIHk9IjI4IiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM4ODg4ODgiIHRleHQtYW5jaG9yPSJtaWRkbGUiPk5vIFRodW1ibmFpbDwvdGV4dD48L3N2Zz4=';
  }
};

/**
 * 释放ObjectURL (防止内存泄漏)
 */
export const releaseThumbnail = (url: string) => {
  if (url.startsWith('blob:')) {
    URL.revokeObjectURL(url);
  }
};

/**
 * 获取视频时长 (调用后端FFmpeg)
 */
export const getVideoDuration = async (videoPath: string): Promise<number> => {
  try {
    const normalizedPath = videoPath.replace(/\\/g, '/');
    const response = await fetch(`http://localhost:8000/api/video/duration?path=${encodeURIComponent(normalizedPath)}`);
    const data = await response.json();
    return data.duration || 0;
  } catch {
    return 0;
  }
};