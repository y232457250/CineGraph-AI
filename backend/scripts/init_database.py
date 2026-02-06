# backend/scripts/init_database.py
"""
数据库初始化脚本
创建新的 SQLAlchemy 数据库并导入配置
"""
import sys
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import init_database, get_db_manager


def main():
    """初始化数据库"""
    print("=" * 50)
    print("CineGraph-AI 数据库初始化")
    print("=" * 50)
    
    # 数据库路径
    db_path = backend_dir / "data" / "cinegraph.db"
    
    # v5 配置路径
    config_path = backend_dir.parent / "config" / "mashup_v5_config.json"
    
    print(f"\n📁 数据库路径: {db_path}")
    print(f"📋 配置文件: {config_path}")
    
    if db_path.exists():
        print(f"\n⚠️  数据库已存在")
        confirm = input("是否重新初始化？这将清除所有数据！(y/N): ")
        if confirm.lower() != 'y':
            print("已取消")
            return
        
        # 备份现有数据库
        backup_path = db_path.with_suffix('.db.backup')
        import shutil
        shutil.copy(db_path, backup_path)
        print(f"✅ 已备份到: {backup_path}")
        
        # 删除现有数据库
        db_path.unlink()
    
    # 初始化数据库
    try:
        manager = init_database(str(db_path), str(config_path))
        print("\n✅ 数据库初始化完成！")
        print(f"\n📊 数据库信息:")
        print(f"   - 路径: {db_path}")
        print(f"   - 大小: {db_path.stat().st_size / 1024:.1f} KB")
        
        # 显示表信息
        session = manager.get_session()
        from sqlalchemy import inspect
        inspector = inspect(manager.engine)
        tables = inspector.get_table_names()
        print(f"   - 表数量: {len(tables)}")
        print(f"   - 表列表: {', '.join(tables)}")
        session.close()
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 50)
    print("下一步：")
    print("1. 设置环境变量 STORE_BACKEND=sqlite")
    print("2. 重启后端服务")
    print("3. 或运行迁移脚本导入现有数据")
    print("=" * 50)
    
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
