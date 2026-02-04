// src/store/taskStore.ts
// 任务队列管理 - 用于批量处理标定和向量化任务

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 任务类型
export type TaskType = 'annotate' | 'vectorize';

// 任务状态
export type TaskStatus = 'pending' | 'running' | 'completed' | 'error';

// 任务项定义
export interface TaskItem {
  id: string;
  type: TaskType;
  status: TaskStatus;
  movieId: string;
  movieTitle: string;
  episodeNumber?: number;
  subtitlePath?: string;
  annotationPath?: string;
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
  error?: string;
  progress?: number; // 0-100
}

// 任务统计
export interface TaskStats {
  total: number;
  pending: number;
  running: number;
  completed: number;
  error: number;
}

interface TaskStore {
  // 标定任务队列
  annotateTasks: TaskItem[];
  // 向量化任务队列
  vectorizeTasks: TaskItem[];
  
  // 添加标定任务
  addAnnotateTask: (task: Omit<TaskItem, 'id' | 'type' | 'status' | 'createdAt'>) => void;
  // 添加向量化任务
  addVectorizeTask: (task: Omit<TaskItem, 'id' | 'type' | 'status' | 'createdAt'>) => void;
  
  // 批量添加标定任务
  addAnnotateTasks: (tasks: Omit<TaskItem, 'id' | 'type' | 'status' | 'createdAt'>[]) => void;
  // 批量添加向量化任务
  addVectorizeTasks: (tasks: Omit<TaskItem, 'id' | 'type' | 'status' | 'createdAt'>[]) => void;
  
  // 移除任务
  removeAnnotateTask: (id: string) => void;
  removeVectorizeTask: (id: string) => void;
  
  // 清空任务队列
  clearAnnotateTasks: () => void;
  clearVectorizeTasks: () => void;
  clearCompletedTasks: (type: TaskType) => void;
  
  // 更新任务状态
  updateAnnotateTask: (id: string, updates: Partial<TaskItem>) => void;
  updateVectorizeTask: (id: string, updates: Partial<TaskItem>) => void;
  
  // 获取任务统计
  getAnnotateStats: () => TaskStats;
  getVectorizeStats: () => TaskStats;
  
  // 检查任务是否已存在
  hasAnnotateTask: (movieId: string, episodeNumber?: number) => boolean;
  hasVectorizeTask: (movieId: string, episodeNumber?: number) => boolean;
}

// 生成唯一ID
const generateId = () => `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// 计算统计信息
const calcStats = (tasks: TaskItem[]): TaskStats => ({
  total: tasks.length,
  pending: tasks.filter(t => t.status === 'pending').length,
  running: tasks.filter(t => t.status === 'running').length,
  completed: tasks.filter(t => t.status === 'completed').length,
  error: tasks.filter(t => t.status === 'error').length,
});

export const useTaskStore = create<TaskStore>()(
  persist(
    (set, get) => ({
      annotateTasks: [],
      vectorizeTasks: [],
      
      // 添加单个标定任务
      addAnnotateTask: (task) => {
        const { movieId, episodeNumber } = task;
        // 检查是否已存在
        if (get().hasAnnotateTask(movieId, episodeNumber)) {
          console.log('标定任务已存在:', movieId, episodeNumber);
          return;
        }
        
        const newTask: TaskItem = {
          ...task,
          id: generateId(),
          type: 'annotate',
          status: 'pending',
          createdAt: Date.now(),
        };
        
        set((state) => ({
          annotateTasks: [...state.annotateTasks, newTask],
        }));
      },
      
      // 添加单个向量化任务
      addVectorizeTask: (task) => {
        const { movieId, episodeNumber } = task;
        // 检查是否已存在
        if (get().hasVectorizeTask(movieId, episodeNumber)) {
          console.log('向量化任务已存在:', movieId, episodeNumber);
          return;
        }
        
        const newTask: TaskItem = {
          ...task,
          id: generateId(),
          type: 'vectorize',
          status: 'pending',
          createdAt: Date.now(),
        };
        
        set((state) => ({
          vectorizeTasks: [...state.vectorizeTasks, newTask],
        }));
      },
      
      // 批量添加标定任务
      addAnnotateTasks: (tasks) => {
        const newTasks: TaskItem[] = [];
        const store = get();
        
        for (const task of tasks) {
          if (!store.hasAnnotateTask(task.movieId, task.episodeNumber)) {
            newTasks.push({
              ...task,
              id: generateId(),
              type: 'annotate',
              status: 'pending',
              createdAt: Date.now(),
            });
          }
        }
        
        if (newTasks.length > 0) {
          set((state) => ({
            annotateTasks: [...state.annotateTasks, ...newTasks],
          }));
        }
      },
      
      // 批量添加向量化任务
      addVectorizeTasks: (tasks) => {
        const newTasks: TaskItem[] = [];
        const store = get();
        
        for (const task of tasks) {
          if (!store.hasVectorizeTask(task.movieId, task.episodeNumber)) {
            newTasks.push({
              ...task,
              id: generateId(),
              type: 'vectorize',
              status: 'pending',
              createdAt: Date.now(),
            });
          }
        }
        
        if (newTasks.length > 0) {
          set((state) => ({
            vectorizeTasks: [...state.vectorizeTasks, ...newTasks],
          }));
        }
      },
      
      // 移除标定任务
      removeAnnotateTask: (id) => {
        set((state) => ({
          annotateTasks: state.annotateTasks.filter(t => t.id !== id),
        }));
      },
      
      // 移除向量化任务
      removeVectorizeTask: (id) => {
        set((state) => ({
          vectorizeTasks: state.vectorizeTasks.filter(t => t.id !== id),
        }));
      },
      
      // 清空标定任务
      clearAnnotateTasks: () => {
        set({ annotateTasks: [] });
      },
      
      // 清空向量化任务
      clearVectorizeTasks: () => {
        set({ vectorizeTasks: [] });
      },
      
      // 清除已完成的任务
      clearCompletedTasks: (type) => {
        if (type === 'annotate') {
          set((state) => ({
            annotateTasks: state.annotateTasks.filter(t => t.status !== 'completed'),
          }));
        } else {
          set((state) => ({
            vectorizeTasks: state.vectorizeTasks.filter(t => t.status !== 'completed'),
          }));
        }
      },
      
      // 更新标定任务
      updateAnnotateTask: (id, updates) => {
        set((state) => ({
          annotateTasks: state.annotateTasks.map(t =>
            t.id === id ? { ...t, ...updates } : t
          ),
        }));
      },
      
      // 更新向量化任务
      updateVectorizeTask: (id, updates) => {
        set((state) => ({
          vectorizeTasks: state.vectorizeTasks.map(t =>
            t.id === id ? { ...t, ...updates } : t
          ),
        }));
      },
      
      // 获取标定任务统计
      getAnnotateStats: () => calcStats(get().annotateTasks),
      
      // 获取向量化任务统计
      getVectorizeStats: () => calcStats(get().vectorizeTasks),
      
      // 检查标定任务是否存在
      hasAnnotateTask: (movieId, episodeNumber) => {
        return get().annotateTasks.some(t => 
          t.movieId === movieId && 
          t.episodeNumber === episodeNumber &&
          (t.status === 'pending' || t.status === 'running')
        );
      },
      
      // 检查向量化任务是否存在
      hasVectorizeTask: (movieId, episodeNumber) => {
        return get().vectorizeTasks.some(t => 
          t.movieId === movieId && 
          t.episodeNumber === episodeNumber &&
          (t.status === 'pending' || t.status === 'running')
        );
      },
    }),
    {
      name: 'cinegraph-task-store',
      version: 1,
    }
  )
);
