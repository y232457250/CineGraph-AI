// src/App/PreviewPanel.tsx
import React, { useRef, useEffect } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import { useNodeStore } from '@/store/nodeStore';

const PreviewPanel = () => {
  const videoRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<videojs.Player | null>(null);
  const { activeNode } = useNodeStore();

  useEffect(() => {
    if (!videoRef.current || !activeNode) return;

    // 初始化video.js (GPU加速解码)
    const player = videojs(videoRef.current, {
      sources: [{ 
        src: `file://${activeNode.videoPath}`, 
        type: 'video/mp4' 
      }],
      autoplay: false,
      controls: true,
      preload: 'metadata',
      html5: {
        nativeAudioTracks: false,
        nativeVideoTracks: false,
        hls: {
          overrideNative: true // 启用WebAssembly解码
        }
      }
    });

    playerRef.current = player;

    // 释放资源 (避免内存泄漏)
    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [activeNode]);

  return (
    <div className="absolute top-4 right-4 w-96 h-52 bg-black rounded-lg overflow-hidden shadow-2xl">
      <div ref={videoRef} className="w-full h-full" />
    </div>
  );
};

export default PreviewPanel;