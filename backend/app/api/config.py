# backend/app/api/config.py
"""
配置文件 API 接口模块
提供配置文件的读取和修改功能
"""

import json
import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 配置路径
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
LLM_CONFIG_PATH = CONFIG_DIR / "llm_providers.yaml"
EMBEDDING_CONFIG_PATH = CONFIG_DIR / "embedding_providers.yaml"
THEME_CONFIG_PATH = CONFIG_DIR / "theme_config.json"
MASHUP_CONFIG_PATH = CONFIG_DIR / "mashup_v5_config.json"
MASHUP_OPTIMIZED_CONFIG_PATH = CONFIG_DIR / "mashup_optimized_config.json"
PROMPT_CONFIG_PATH = CONFIG_DIR / "prompt_config.json"
SETTINGS_CONFIG_PATH = BASE_DIR / "backend" / "config" / "settings.yaml"

router = APIRouter(prefix="/api/config", tags=["Config"])


# ==================== 数据模型 ====================

class ConfigContent(BaseModel):
    content: str

class ConfigUpdate(BaseModel):
    content: str


# ==================== API 路由 ====================

@router.get("/llm-providers")
async def get_llm_providers_config():
    """获取 LLM 提供者配置文件内容"""
    if not LLM_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")
    
    try:
        with open(LLM_CONFIG_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "path": str(LLM_CONFIG_PATH)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置文件失败: {str(e)}")


@router.put("/llm-providers")
async def update_llm_providers_config(config: ConfigUpdate):
    """更新 LLM 提供者配置文件"""
    # 验证 YAML 格式
    try:
        yaml.safe_load(config.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 格式错误: {str(e)}")
    
    # 备份原配置
    backup_path = LLM_CONFIG_PATH.with_suffix(".yaml.bak")
    if LLM_CONFIG_PATH.exists():
        try:
            with open(LLM_CONFIG_PATH, "r", encoding="utf-8") as f:
                backup_content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(backup_content)
        except Exception as e:
            print(f"⚠️ 备份配置文件失败: {e}")
    
    # 写入新配置
    try:
        with open(LLM_CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(config.content)
        
        # 尝试重新加载 LLM 客户端配置
        try:
            from app.api.llm import llm_client
            llm_client.reload_config()
        except Exception as e:
            print(f"⚠️ 重新加载 LLM 配置失败: {e}")
        
        return {"success": True, "message": "配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置文件失败: {str(e)}")


@router.get("/embedding-providers")
async def get_embedding_providers_config():
    """获取 Embedding 提供者配置文件内容"""
    if not EMBEDDING_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")
    
    try:
        with open(EMBEDDING_CONFIG_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "path": str(EMBEDDING_CONFIG_PATH)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置文件失败: {str(e)}")


@router.put("/embedding-providers")
async def update_embedding_providers_config(config: ConfigUpdate):
    """更新 Embedding 提供者配置文件"""
    # 验证 YAML 格式
    try:
        yaml.safe_load(config.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 格式错误: {str(e)}")
    
    # 备份原配置
    backup_path = EMBEDDING_CONFIG_PATH.with_suffix(".yaml.bak")
    if EMBEDDING_CONFIG_PATH.exists():
        try:
            with open(EMBEDDING_CONFIG_PATH, "r", encoding="utf-8") as f:
                backup_content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(backup_content)
        except Exception as e:
            print(f"⚠️ 备份配置文件失败: {e}")
    
    # 写入新配置
    try:
        with open(EMBEDDING_CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(config.content)
        return {"success": True, "message": "配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置文件失败: {str(e)}")


@router.get("/theme")
async def get_theme_config():
    """获取主题配置"""
    if not THEME_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="主题配置文件不存在")
    
    try:
        import json
        with open(THEME_CONFIG_PATH, "r", encoding="utf-8") as f:
            content = json.load(f)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取主题配置失败: {str(e)}")


@router.get("/mashup")
async def get_mashup_config():
    """获取混剪配置"""
    if not MASHUP_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="混剪配置文件不存在")
    
    try:
        with open(MASHUP_CONFIG_PATH, "r", encoding="utf-8") as f:
            content = json.load(f)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取混剪配置失败: {str(e)}")


@router.get("/mashup-optimized")
async def get_mashup_optimized_config():
    """获取混剪优化配置（原始文件内容）"""
    if not MASHUP_OPTIMIZED_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="混剪优化配置文件不存在")

    try:
        with open(MASHUP_OPTIMIZED_CONFIG_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "path": str(MASHUP_OPTIMIZED_CONFIG_PATH)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取混剪优化配置失败: {str(e)}")


@router.put("/mashup-optimized")
async def update_mashup_optimized_config(config: ConfigUpdate):
    """更新混剪优化配置文件"""
    # 验证 JSON 格式
    try:
        parsed = json.loads(config.content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 格式错误: {str(e)}")

    # 备份原配置
    backup_path = MASHUP_OPTIMIZED_CONFIG_PATH.with_suffix(".json.bak")
    if MASHUP_OPTIMIZED_CONFIG_PATH.exists():
        try:
            with open(MASHUP_OPTIMIZED_CONFIG_PATH, "r", encoding="utf-8") as f:
                backup_content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(backup_content)
        except Exception as e:
            print(f"⚠️ 备份混剪优化配置文件失败: {e}")

    # 写入新配置
    try:
        with open(MASHUP_OPTIMIZED_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": "混剪优化配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存混剪优化配置文件失败: {str(e)}")


@router.get("/prompt")
async def get_prompt_config():
    """获取提示词配置"""
    if not PROMPT_CONFIG_PATH.exists():
        # 返回默认配置
        return {
            "version": "1.0",
            "description": "语义标注提示词配置",
            "annotation_prompt": {
                "system_prompt": "你是专业的影视混剪创作专家...",
                "user_prompt_template": "..."
            }
        }
    
    try:
        with open(PROMPT_CONFIG_PATH, "r", encoding="utf-8") as f:
            content = json.load(f)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取提示词配置失败: {str(e)}")


@router.put("/prompt")
async def update_prompt_config(config: ConfigUpdate):
    """更新提示词配置文件"""
    # 验证 JSON 格式
    try:
        parsed = json.loads(config.content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 格式错误: {str(e)}")
    
    # 备份原配置
    backup_path = PROMPT_CONFIG_PATH.with_suffix(".json.bak")
    if PROMPT_CONFIG_PATH.exists():
        try:
            with open(PROMPT_CONFIG_PATH, "r", encoding="utf-8") as f:
                backup_content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(backup_content)
        except Exception as e:
            print(f"⚠️ 备份提示词配置文件失败: {e}")
    
    # 写入新配置
    try:
        with open(PROMPT_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": "提示词配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存提示词配置文件失败: {str(e)}")


@router.get("/settings")
async def get_settings_config():
    """获取系统设置配置（原始文件内容）"""
    if not SETTINGS_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="系统设置配置文件不存在")

    try:
        with open(SETTINGS_CONFIG_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "path": str(SETTINGS_CONFIG_PATH)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取系统设置配置失败: {str(e)}")


@router.put("/settings")
async def update_settings_config(config: ConfigUpdate):
    """更新系统设置配置文件"""
    # 验证 YAML 格式
    try:
        yaml.safe_load(config.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 格式错误: {str(e)}")

    # 备份原配置
    backup_path = SETTINGS_CONFIG_PATH.with_suffix(".yaml.bak")
    if SETTINGS_CONFIG_PATH.exists():
        try:
            with open(SETTINGS_CONFIG_PATH, "r", encoding="utf-8") as f:
                backup_content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(backup_content)
        except Exception as e:
            print(f"⚠️ 备份系统设置配置文件失败: {e}")

    # 写入新配置
    try:
        SETTINGS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(config.content)

        return {"success": True, "message": "系统设置配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存系统设置配置文件失败: {str(e)}")


@router.get("/list")
async def list_config_files():
    """列出所有可用的配置文件"""
    configs = []
    
    config_files = [
        ("llm_providers.yaml", "LLM 提供者配置", "yaml"),
        ("prompt_config.json", "提示词配置", "json"),
        ("theme_config.json", "主题配置", "json"),
        ("mashup_v5_config.json", "混剪配置 V5", "json"),
        ("mashup_optimized_config.json", "混剪优化配置", "json"),
    ]
    
    for filename, description, file_type in config_files:
        path = CONFIG_DIR / filename
        configs.append({
            "filename": filename,
            "description": description,
            "type": file_type,
            "exists": path.exists(),
            "path": str(path)
        })
    
    return {"configs": configs}
