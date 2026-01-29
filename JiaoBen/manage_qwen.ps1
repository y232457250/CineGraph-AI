# manage_qwen.ps1
# 一键管理 Qwen3-4B 和 Qwen3-Embedding 服务
# 作者：Qwen | 适配路径：D:\AI\CineGraph-AI\JiaoBen

 $ projectPath = "D:\AI\CineGraph-AI\JiaoBen"

# 检查 Docker 是否运行
function CheckDocker {
    try {
         $ dockerInfo = docker info --format '{{.ServerVersion}}' 2>&1
        if ( $ ?) {
            return  $ true
        } else {
            Write-Host "❌ Docker 未运行！请先启动 Docker Desktop。" -ForegroundColor Red
            return  $ false
        }
    } catch {
        Write-Host "❌ 无法连接 Docker，请确保 Docker Desktop 正在运行。" -ForegroundColor Red
        return  $ false
    }
}

# 进入项目目录
Set-Location  $ projectPath

function Show-Menu {
    Clear-Host
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "🚀 Qwen3 服务管理器 (RTX 5070 Ti 12GB)" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "1. 启动 Qwen3-Chat-4B（语义分析）"
    Write-Host "2. 启动 Qwen3-Embedding-4B（向量化）"
    Write-Host "3. 停止所有服务"
    Write-Host "4. 查看服务状态"
    Write-Host "5. 退出"
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "💡 提示：两个大模型不能同时运行（显存限制）" -ForegroundColor Yellow
    Write-Host ""
}

function Start-QwenChat {
    Write-Host "⏳ 正在停止 Embedding 服务（如有）..."
    docker compose down qwen3-emb 2>&1 | Out-Null

    Write-Host "🚀 启动 Qwen3-Chat-:4B 服务..."
    docker compose up -d qwen3-chat
    Write-Host "✅ Qwen3-Chat 服务已启动！" -ForegroundColor Green
    Write-Host "   API 地址: http://localhost:8001/v1/chat/completions"
}

function Start-QwenEmb {
    Write-Host "⏳ 正在停止 Chat 服务（如有）..."
    docker compose down qwen3-chat 2>&1 | Out-Null

    Write-Host "🚀 启动 Qwen3-Embedding-4B 服务..."
    docker compose up -d qwen3-emb
    Write-Host "✅ Qwen3-Embedding 服务已启动！" -ForegroundColor Green
    Write-Host "   API 地址: http://localhost:8000/v1/embeddings"
}

function Stop-All {
    Write-Host "🛑 正在停止所有服务..."
    docker compose down
    Write-Host "✅ 所有服务已停止。" -ForegroundColor Green
}

function Show-Status {
    Write-Host "🔍 当前服务状态："
    docker compose ps
}

# 主循环
do {
    Show-Menu
     $choice = Read-Host "请输入选项 [1-5]"

    switch ( $choice) {
        '1' { Start-QwenChat }
        '2' { Start-QwenEmb }
        '3' { Stop-All }
        '4' { Show-Status }
        '5' { 
            Write-Host "👋 再见！" -ForegroundColor Cyan
            exit 0
        }
        default {
            Write-Host "⚠️ 无效选项，请输入 1-5。" -ForegroundColor Yellow
            Start-Sleep -Seconds 1
        }
    }

    Write-Host ""
    pause
} while ( $true)