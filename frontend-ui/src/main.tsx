import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css"; // 确保 index.css 引入了 tailwind

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);