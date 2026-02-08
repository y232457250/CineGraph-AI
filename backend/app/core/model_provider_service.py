# backend/app/core/model_provider_service.py
"""
模型提供者管理服务
从数据库读取模型配置，统一管理 LLM 和 Embedding 提供者
替代原有的 YAML 配置文件方式
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from app.models.database import (
    ModelProvider, DatabaseManager, get_db_manager, Base
)


class ModelProviderService:
    """
    模型提供者管理服务
    
    职责:
    - 从数据库读取/写入模型配置
    - 提供 CRUD 操作
    - 管理活跃提供者
    - 确保数据库表和默认数据已初始化
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._ensure_db_ready()
    
    def _ensure_db_ready(self):
        """确保数据库表已创建且有默认数据"""
        try:
            db = get_db_manager()
            # 确保 model_providers 表存在
            Base.metadata.create_all(db.engine)
            # 检查是否需要初始化默认数据
            session = db.get_session()
            try:
                count = session.query(ModelProvider).count()
                if count == 0:
                    db._init_default_model_providers(session)
            finally:
                session.close()
        except Exception as e:
            print(f"⚠️ 模型提供者数据库初始化失败: {e}")
    
    def _get_session(self):
        """获取数据库会话"""
        return get_db_manager().get_session()
    
    # ==================== 查询 ====================
    
    def list_providers(self, category: str = None, enabled_only: bool = True) -> List[Dict]:
        """
        列出模型提供者
        
        Args:
            category: 过滤类别 ("llm" 或 "embedding")，None 返回全部
            enabled_only: 是否只返回启用的
        """
        session = self._get_session()
        try:
            query = session.query(ModelProvider)
            if category:
                query = query.filter(ModelProvider.category == category)
            if enabled_only:
                query = query.filter(ModelProvider.enabled == True)
            query = query.order_by(ModelProvider.sort_order, ModelProvider.created_at)
            return [p.to_dict() for p in query.all()]
        finally:
            session.close()
    
    def get_provider(self, provider_id: str) -> Optional[Dict]:
        """获取单个提供者（含完整信息）"""
        session = self._get_session()
        try:
            provider = session.query(ModelProvider).filter_by(id=provider_id).first()
            return provider.to_dict() if provider else None
        finally:
            session.close()
    
    def get_provider_config(self, provider_id: str) -> Optional[Dict]:
        """获取提供者的完整配置（含解密的 API Key，供内部调用）"""
        session = self._get_session()
        try:
            provider = session.query(ModelProvider).filter_by(id=provider_id).first()
            return provider.to_provider_config() if provider else None
        finally:
            session.close()
    
    def get_active_provider(self, category: str) -> Optional[Dict]:
        """获取某类别的当前激活提供者"""
        session = self._get_session()
        try:
            provider = session.query(ModelProvider).filter_by(
                category=category, is_active=True
            ).first()
            if provider:
                return provider.to_dict()
            # 回退：返回该类别的第一个启用的提供者
            provider = session.query(ModelProvider).filter_by(
                category=category, enabled=True
            ).order_by(ModelProvider.sort_order).first()
            if provider:
                provider.is_active = True
                session.commit()
                return provider.to_dict()
            return None
        finally:
            session.close()
    
    def get_active_provider_config(self, category: str) -> Optional[Dict]:
        """获取某类别的当前激活提供者的完整配置"""
        session = self._get_session()
        try:
            provider = session.query(ModelProvider).filter_by(
                category=category, is_active=True
            ).first()
            if not provider:
                provider = session.query(ModelProvider).filter_by(
                    category=category, enabled=True
                ).order_by(ModelProvider.sort_order).first()
            return provider.to_provider_config() if provider else None
        finally:
            session.close()
    
    def get_active_provider_id(self, category: str) -> Optional[str]:
        """获取某类别的当前激活提供者ID"""
        session = self._get_session()
        try:
            provider = session.query(ModelProvider).filter_by(
                category=category, is_active=True
            ).first()
            return provider.id if provider else None
        finally:
            session.close()
    
    # ==================== 增删改 ====================
    
    def create_provider(self, data: Dict) -> Dict:
        """
        创建新的模型提供者
        
        Args:
            data: 提供者配置数据
        
        Returns:
            创建后的提供者数据
        """
        session = self._get_session()
        try:
            provider_id = data.get('id', '')
            if not provider_id:
                # 自动生成ID
                import hashlib
                raw = f"{data.get('category', 'llm')}_{data.get('model', '')}_{datetime.utcnow().timestamp()}"
                provider_id = hashlib.md5(raw.encode()).hexdigest()[:16]
            
            # 检查ID是否已存在
            existing = session.query(ModelProvider).filter_by(id=provider_id).first()
            if existing:
                raise ValueError(f"提供者ID已存在: {provider_id}")
            
            extra_config = data.get('extra_config', {})
            if isinstance(extra_config, dict):
                extra_config = json.dumps(extra_config, ensure_ascii=False)
            
            provider = ModelProvider(
                id=provider_id,
                name=data.get('name', provider_id),
                category=data.get('category', 'llm'),
                provider_type=data.get('provider_type', 'commercial'),
                local_mode=data.get('local_mode', ''),
                base_url=data.get('base_url', ''),
                model=data.get('model', ''),
                api_key=data.get('api_key', ''),
                max_tokens=data.get('max_tokens', 2000),
                temperature=data.get('temperature', 0.7),
                timeout=data.get('timeout', 60),
                dimension=data.get('dimension', 0),
                api_style=data.get('api_style', 'openai'),
                description=data.get('description', ''),
                price_info=data.get('price_info', ''),
                is_active=False,
                is_default=False,
                sort_order=data.get('sort_order', 100),
                enabled=data.get('enabled', True),
                extra_config=extra_config,
            )
            session.add(provider)
            session.commit()
            
            result = provider.to_dict()
            return result
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def update_provider(self, provider_id: str, data: Dict) -> Optional[Dict]:
        """
        更新模型提供者
        
        Args:
            provider_id: 提供者ID
            data: 需要更新的字段
        
        Returns:
            更新后的提供者数据
        """
        session = self._get_session()
        try:
            provider = session.query(ModelProvider).filter_by(id=provider_id).first()
            if not provider:
                return None
            
            # 可更新的字段
            updatable_fields = [
                'name', 'base_url', 'model', 'api_key', 'max_tokens',
                'temperature', 'timeout', 'dimension', 'api_style',
                'description', 'price_info', 'sort_order', 'enabled',
                'provider_type', 'local_mode', 'category',
            ]
            
            for field in updatable_fields:
                if field in data:
                    setattr(provider, field, data[field])
            
            if 'extra_config' in data:
                extra = data['extra_config']
                if isinstance(extra, dict):
                    extra = json.dumps(extra, ensure_ascii=False)
                provider.extra_config = extra
            
            provider.updated_at = datetime.utcnow()
            session.commit()
            
            return provider.to_dict()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def delete_provider(self, provider_id: str) -> bool:
        """
        删除模型提供者（每个类别至少保留1个模型）
        
        Args:
            provider_id: 提供者ID
        
        Returns:
            是否删除成功
        """
        session = self._get_session()
        try:
            provider = session.query(ModelProvider).filter_by(id=provider_id).first()
            if not provider:
                return False
            
            # 检查该类别是否至少还有1个其他模型
            same_category_count = session.query(ModelProvider).filter_by(
                category=provider.category
            ).count()
            if same_category_count <= 1:
                raise ValueError(f"每个类别至少需要保留1个模型，当前 {provider.category} 类别仅剩1个")
            
            # 如果删除的是活跃模型，自动切换到同类别其他模型
            if provider.is_active:
                alt = session.query(ModelProvider).filter(
                    ModelProvider.category == provider.category,
                    ModelProvider.id != provider_id,
                    ModelProvider.enabled == True
                ).first()
                if alt:
                    alt.is_active = True
            
            session.delete(provider)
            session.commit()
            return True
        except ValueError:
            raise
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def set_active_provider(self, provider_id: str, category: str) -> bool:
        """
        设置某类别的活跃提供者
        
        Args:
            provider_id: 要激活的提供者ID
            category: "llm" 或 "embedding"
        
        Returns:
            是否设置成功
        """
        session = self._get_session()
        try:
            # 先验证目标提供者存在且类别匹配
            target = session.query(ModelProvider).filter_by(
                id=provider_id, category=category
            ).first()
            if not target:
                raise ValueError(f"提供者不存在或类别不匹配: {provider_id}")
            
            # 将该类别所有提供者设为非活跃
            session.query(ModelProvider).filter_by(
                category=category, is_active=True
            ).update({'is_active': False})
            
            # 激活目标
            target.is_active = True
            target.updated_at = datetime.utcnow()
            session.commit()
            
            print(f"✅ 已切换{category}提供者: {target.name} ({provider_id})")
            return True
        except ValueError:
            raise
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def toggle_provider(self, provider_id: str, enabled: bool) -> bool:
        """启用/禁用提供者"""
        session = self._get_session()
        try:
            provider = session.query(ModelProvider).filter_by(id=provider_id).first()
            if not provider:
                return False
            provider.enabled = enabled
            # 如果禁用了活跃的提供者，需要切换到其他提供者
            if not enabled and provider.is_active:
                provider.is_active = False
                # 找到同类别的其他启用的提供者
                alt = session.query(ModelProvider).filter(
                    ModelProvider.category == provider.category,
                    ModelProvider.enabled == True,
                    ModelProvider.id != provider_id
                ).order_by(ModelProvider.sort_order).first()
                if alt:
                    alt.is_active = True
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def reset_to_defaults(self, category: str = None) -> int:
        """
        重置为默认配置（删除用户添加的，重建系统预置的）
        
        Args:
            category: 要重置的类别，None 重置全部
        
        Returns:
            重置的数量
        """
        session = self._get_session()
        try:
            query = session.query(ModelProvider)
            if category:
                query = query.filter_by(category=category)
            
            # 删除所有
            count = query.delete()
            session.commit()
            
            # 重新初始化默认数据
            db = get_db_manager()
            db._init_default_model_providers(session)
            
            return count
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def import_from_yaml(self, yaml_content: str, category: str) -> int:
        """
        从 YAML 配置导入模型提供者（用于迁移旧配置）
        
        Args:
            yaml_content: YAML 格式的配置内容
            category: "llm" 或 "embedding"
        
        Returns:
            导入的数量
        """
        import yaml
        config = yaml.safe_load(yaml_content)
        if not config:
            return 0
        
        count = 0
        for key, value in config.items():
            if not isinstance(value, dict) or 'base_url' not in value:
                continue
            
            data = {
                'id': f"imported_{key}",
                'name': value.get('name', key),
                'category': category,
                'provider_type': value.get('type', 'local'),
                'local_mode': value.get('local_mode', ''),
                'base_url': value.get('base_url', ''),
                'model': value.get('model', ''),
                'api_key': value.get('api_key', ''),
                'max_tokens': value.get('max_tokens', 2000),
                'temperature': value.get('temperature', 0.7),
                'timeout': value.get('timeout', 60),
                'dimension': value.get('dimension', 0),
                'api_style': value.get('api_style', 'openai'),
                'description': value.get('description', ''),
                'sort_order': 200 + count,
            }
            
            try:
                self.create_provider(data)
                count += 1
            except ValueError:
                # ID已存在，跳过
                pass
        
        return count


# 全局单例
_service: Optional[ModelProviderService] = None


def get_model_provider_service() -> ModelProviderService:
    """获取模型提供者服务单例"""
    global _service
    if _service is None:
        _service = ModelProviderService()
    return _service
