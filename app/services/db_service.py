import sqlite3
import os
from typing import List, Dict, Any, Tuple, Optional

# 数据库文件路径
# 获取当前文件(db_service.py)的目录: .../app/services
current_dir = os.path.dirname(os.path.abspath(__file__))
# 项目根目录: .../app/services/../../ -> .../Novel_setting_system
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
DB_PATH = os.path.join(project_root, 'novel_system.db')

def get_db_connection():
    """
    获取数据库连接。
    设置 row_factory 为 sqlite3.Row，以便可以通过列名访问结果。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # 启用外键约束
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """
    初始化数据库：如果数据库文件不存在或表结构缺失，则创建并执行 schema.sql。
    """
    should_init = False
    if not os.path.exists(DB_PATH):
        should_init = True
    else:
        # 检查关键表是否存在
        try:
            conn = get_db_connection()
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='novels'")
            if cursor.fetchone() is None:
                should_init = True
            conn.close()
        except Exception:
            should_init = True

    if should_init:
        print(f"数据库不存在或表结构缺失，正在初始化: {DB_PATH}")
        conn = get_db_connection()
        
        # 获取 schema.sql 的绝对路径
        schema_path = os.path.join(os.path.dirname(__file__), '..', '..', 'schema.sql')
        schema_path = os.path.abspath(schema_path)
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.close()
        print(f"数据库已初始化: {DB_PATH}")

def execute_query(query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
    """
    执行查询语句 (SELECT)。
    返回字典列表。
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(query, params)
        # 将 sqlite3.Row 对象转换为普通字典
        result = [dict(row) for row in cursor.fetchall()]
        return result
    finally:
        conn.close()

def execute_commit(query: str, params: Tuple = ()) -> int:
    """
    执行提交语句 (INSERT, UPDATE, DELETE)。
    返回 lastrowid (对于INSERT) 或 rowcount (对于UPDATE/DELETE)。
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        if query.strip().upper().startswith("INSERT"):
            return cursor.lastrowid
        else:
            return cursor.rowcount
    finally:
        conn.close()

def execute_transaction(operations: List[Dict[str, Any]]) -> bool:
    """
    执行事务。
    operations: 包含多个操作的列表，每个操作是 {'query': str, 'params': tuple}
    """
    conn = get_db_connection()
    try:
        for op in operations:
            conn.execute(op['query'], op.get('params', ()))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"事务执行失败: {e}")
        raise e # 抛出异常以便上层处理
    finally:
        conn.close()
