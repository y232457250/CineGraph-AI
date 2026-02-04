// src/App/TimelinePanel.tsx
import { useRef, useEffect, useState } from 'react';

const TimelinePanel = ({ activeNode }: { activeNode?: any | null }) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    if (!activeNode || !timelineRef.current) return;

    // 仅在视频加载后更新时间线
    const updateTimeline = () => {
      if (activeNode.duration) {
        const progress = (currentTime / activeNode.duration) * 100;
        timelineRef.current!.style.setProperty('--progress', `${progress}%`);
      }
    };

    updateTimeline();
  }, [currentTime, activeNode]);

  const handleTimeUpdate = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
  };

  return (
    <div className="w-full bg-[#2d2d3a] rounded-lg p-2 shadow-lg">
      <div className="flex items-center">
        <input 
          type="range" 
          min="0" 
          max={activeNode?.duration || 0} 
          value={currentTime} 
          onChange={handleTimeUpdate}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
        />
        <div className="ml-2 text-white">
          {currentTime.toFixed(2)}s / {activeNode?.duration?.toFixed(2)}s
        </div>
      </div>
    </div>
  );
};

export default TimelinePanel;