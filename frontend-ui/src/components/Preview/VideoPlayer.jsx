import React, { useRef, useEffect } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

const VideoPlayer = ({ videoPath, startTime = 0, endTime = 0 }) => {
  const videoRef = useRef(null);
  const playerRef = useRef(null);

  useEffect(() => {
    // 初始化video.js (GPU加速)
    const player = videojs(videoRef.current, {
      sources: [{ src: videoPath, type: 'video/mp4' }],
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

    // 设置时间范围 (帧精确控制)
    if (startTime > 0 || endTime > 0) {
      player.currentTime(startTime);
      player.on('timeupdate', () => {
        if (player.currentTime() >= endTime) {
          player.pause();
        }
      });
    }

    return () => {
      player.dispose();
    };
  }, [videoPath, startTime, endTime]);

  return (
    <div className="video-player">
      <video ref={videoRef} className="video-js vjs-default-skin" />
    </div>
  );
};