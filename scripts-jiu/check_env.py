import sys
import os
import torch
import platform

def print_separator():
    print("-" * 50)

def check_env():
    print_separator()
    print("🚀 影视台词搜索引擎 - 环境自检程序")
    print_separator()

    # 1. 系统与 Python 版本
    # 避免调用 platform.system()/platform.release()（这些在某些机器上会触发阻塞的网络查找）
    if os.name == 'nt':
        system_name = 'Windows'
    elif os.name == 'posix':
        system_name = 'POSIX'
    else:
        system_name = os.name
    print(f"[1] 操作系统: {system_name}  (sys.platform={sys.platform}, os.name={os.name})")
    print(f"[2] Python 版本: {sys.version.split()[0]}")
    
    # 2. CUDA 与 GPU 检查
    print_separator()
    cuda_available = torch.cuda.is_available()
    print(f"[3] PyTorch CUDA 可用性: {cuda_available}")
    
    if cuda_available:
        print(f"    - GPU 型号: {torch.cuda.get_device_name(0)}")
        print(f"    - CUDA 版本: {torch.version.cuda}")
        total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"    - 显存总量: {total_vram:.2f} GB")
        if total_vram < 14:
            print("    ⚠️ 警告: 显存不足 16GB，请务必使用 4-bit 量化加载模型。")
    else:
        print("    ❌ 错误: 未检测到可用 GPU，请检查显卡驱动或 PyTorch 是否安装正确。")

    # 3. 核心依赖库检查
    print_separator()
    print("[4] 核心库安装状态:")
    libraries = [
        "transformers", 
        "sentence_transformers", 
        "chromadb", 
        "fastapi", 
        "bitsandbytes",  # 4-bit 量化关键
        "pysrt",         # 字幕解析
        "cv2",           # OpenCV 视频处理
        "accelerate"     # 模型分布式加载
    ]

    missing_libs = []
    for lib in libraries:
        try:
            if lib == "cv2":
                import cv2
                ver = cv2.__version__
            elif lib == "pysrt":
                import pysrt
                ver = "已安装"
            else:
                module = __import__(lib)
                ver = getattr(module, "__version__", "已安装")
            print(f"    ✅ {lib.ljust(22)}: {ver}")
        except ImportError:
            print(f"    ❌ {lib.ljust(22)}: 未安装")
            missing_libs.append(lib)

    # 4. Bitsandbytes 专项检查 (量化加载必须)
    if "bitsandbytes" not in missing_libs:
        try:
            from bitsandbytes.nn import Linear4bit
            print("    ✅ Bitsandbytes 量化组件正常工作")
        except Exception as e:
            print(f"    ❌ Bitsandbytes 加载失败 (可能是 Windows 兼容性问题): {e}")

    # 5. FFmpeg 检查
    print_separator()
    ffmpeg_check = os.system("ffmpeg -version > nul 2>&1") if platform.system() == "Windows" else os.system("ffmpeg -version > /dev/null 2>&1")
    if ffmpeg_check == 0:
        print("[5] FFmpeg 状态: ✅ 已安装并可用")
    else:
        print("[5] FFmpeg 状态: ❌ 未检测到 FFmpeg，请安装并添加到环境变量。")

    print_separator()
    if not missing_libs and cuda_available:
        print("🎉 恭喜！基础环境搭建完成，可以开始模型加载测试。")
    else:
        print("🛠️ 请根据上方 [❌] 提示修复环境后再继续。")
    print_separator()

if __name__ == "__main__":
    check_env()