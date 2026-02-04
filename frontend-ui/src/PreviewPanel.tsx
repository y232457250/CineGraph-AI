// src/App/PreviewPanel.tsx
import { useRef, useEffect } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

const PreviewPanel = ({ activeNode }: { activeNode?: any | null }) => {
  const videoRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<any | null>(null);

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
    <div className="w-96 h-52 bg-black rounded-lg overflow-hidden shadow-2xl">
      <div ref={videoRef} className="w-full h-full" />
    </div>
  );
};

export default PreviewPanel;