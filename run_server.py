import uvicorn
import os
import sys

# 1. 路径自动配置
# 根目录: E:\GeoSensing_Agent_System
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# API 目录: E:\GeoSensing_Agent_System\api_services
API_DIR = os.path.join(BASE_DIR, "api_services")
# 工具目录: E:\GeoSensing_Agent_System\tools
TOOLS_DIR = os.path.join(BASE_DIR, "tools")


def start_api():
    print("=== GeoSensing Agent API 启动器 (路径修正版) ===")

    # 2. 核心逻辑：注入环境变量，确保工具包可被识别
    # 将项目根目录、API目录、工具目录全部加入 PYTHONPATH
    env = os.environ.copy()
    new_paths = [BASE_DIR, API_DIR, TOOLS_DIR]
    env["PYTHONPATH"] = os.pathsep.join(new_paths) + os.pathsep + env.get("PYTHONPATH", "")

    # 将这些路径也加入当前进程的 sys.path
    for path in new_paths:
        if path not in sys.path:
            sys.path.insert(0, path)

    print(f"📍 项目根目录: {BASE_DIR}")
    print(f"📂 API 文件夹: {API_DIR}")
    print(f"🛠️ 工具包路径: {TOOLS_DIR}")
    print("-" * 45)

    # 3. 启动服务
    # 使用 app_dir 指定 allAPI 所在的文件夹，这能解决子进程找不到模块的问题
    uvicorn.run(
        "allAPI:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir=API_DIR,  # <--- 关键修复：显式指定应用目录
        env_file=None  # 确保不被外部环境文件干扰
    )


if __name__ == "__main__":
    try:
        start_api()
    except KeyboardInterrupt:
        print("\n🛑 服务已停止。")
    except Exception as e:
        print(f"❌ 启动失败: {e}")