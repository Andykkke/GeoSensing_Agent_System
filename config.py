import os

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 定义 GeoJSON 数据存储路径
GEOJSON_DIR = os.path.join(PROJECT_ROOT, "data", "output")
if not os.path.exists(GEOJSON_DIR):
    os.makedirs(GEOJSON_DIR)

def get_geojson_path(filename: str) -> str:
    """根据文件名生成完整的数据存储路径"""
    if not filename.endswith(".geojson") and not filename.endswith(".json"):
        filename += ".geojson"
    return os.path.join(GEOJSON_DIR, filename)

def save_geojson_file(data: dict, filename: str) -> str:
    """保存数据到本地并返回路径"""
    import json
    path = get_geojson_path(filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path

# 对应 allAPI.py 中引用的会话 ID 变量
from contextvars import ContextVar
current_conversation_id: ContextVar[str] = ContextVar("current_conversation_id", default="default")