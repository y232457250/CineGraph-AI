#!/usr/bin/env python3
"""
验证 CineGraph-AI 设置脚本
检查数据库、存储层和所有关键组件
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def check_imports():
    """检查所有关键导入"""
    print("\n📦 检查依赖导入...")
    
    checks = [
        ("SQLAlchemy", lambda: __import__("sqlalchemy")),
        ("FastAPI", lambda: __import__("fastapi")),
        ("ChromaDB", lambda: __import__("chromadb")),
        ("Pydantic", lambda: __import__("pydantic")),
        ("PyYAML", lambda: __import__("yaml")),
    ]
    
    all_ok = True
    for name, check_fn in checks:
        try:
            check_fn()
            print(f"   ✅ {name}")
        except ImportError as e:
            print(f"   ❌ {name}: {e}")
            all_ok = False
    
    return all_ok


def check_database():
    """检查数据库"""
    print("\n🗄️  检查数据库...")
    
    db_path = backend_dir / "data" / "cinegraph.db"
    
    if not db_path.exists():
        print(f"   ⚠️  数据库不存在: {db_path}")
        print("   请先运行: python scripts/init_database.py")
        return False
    
    try:
        from app.models.database import get_db_manager
        db_manager = get_db_manager()
        session = db_manager.get_session()
        
        # 检查表
        from sqlalchemy import inspect
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        
        required_tables = ['movies', 'lines', 'projects', 'canvas_nodes', 'system_config']
        missing = [t for t in required_tables if t not in tables]
        
        if missing:
            print(f"   ❌ 缺少表: {', '.join(missing)}")
            return False
        
        print(f"   ✅ 数据库正常 ({len(tables)} 个表)")
        session.close()
        return True
        
    except Exception as e:
        print(f"   ❌ 数据库检查失败: {e}")
        return False


def check_storage():
    """检查存储层"""
    print("\n💾 检查存储层...")
    
    try:
        from app.core.store import get_unified_store, get_movie_store
        
        unified = get_unified_store()
        print("   ✅ unified_store 初始化成功")
        
        # 尝试简单操作
        movies = unified.list_movies()
        print(f"   ✅ 已存储 {len(movies)} 个影片")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 存储层检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_settings():
    """检查设置模块"""
    print("\n⚙️  检查设置模块...")
    
    try:
        from app.api.settings import load_settings_from_db, init_default_settings
        
        # 初始化默认设置
        init_default_settings()
        
        # 加载设置
        settings = load_settings_from_db()
        
        required_keys = ['annotation', 'vectorization', 'paths', 'app']
        missing = [k for k in required_keys if k not in settings]
        
        if missing:
            print(f"   ❌ 缺少设置项: {', '.join(missing)}")
            return False
        
        print("   ✅ 设置模块正常")
        return True
        
    except Exception as e:
        print(f"   ❌ 设置检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_canvas():
    """检查无限画布功能"""
    print("\n🎨 检查无限画布...")
    
    try:
        from app.core.store import get_unified_store
        store = get_unified_store()
        
        # 列出项目
        projects = store.list_projects()
        print(f"   ✅ 已有 {len(projects)} 个项目")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 画布检查失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("CineGraph-AI 设置验证")
    print("=" * 60)
    
    results = {
        "依赖导入": check_imports(),
        "数据库": check_database(),
        "存储层": check_storage(),
        "设置模块": check_settings(),
        "无限画布": check_canvas(),
    }
    
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    
    for name, ok in results.items():
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"   {name}: {status}")
    
    all_ok = all(results.values())
    
    if all_ok:
        print("\n🎉 所有检查通过！系统已就绪。")
        print("\n启动服务:")
        print("   python main.py")
    else:
        print("\n⚠️  部分检查未通过，请查看上文并修复问题。")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
