// src/App/App.tsx
import React from 'react';
import CanvasView from './CanvasView';
import PreviewPanel from './PreviewPanel';
import ResourcePanel from './ResourcePanel';
import TimelinePanel from './TimelinePanel';
import PropertyPanel from './PropertyPanel';

const App = () => {
  return (
    <div className="relative w-full h-full bg-gradient-to-br from-gray-900 to-black">
      <ResourcePanel />
      <CanvasView />
      <PreviewPanel />
      <TimelinePanel />
      <PropertyPanel />
    </div>
  );
};

export default App;