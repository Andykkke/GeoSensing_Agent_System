import sqlite3
import os

db_path = r"E:\GeoSensing_Agent_System\data\databases\satellite_data.db"

if not os.path.exists(db_path):
    print(f"❌ 错误：找不到数据库文件 {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # 在 test5.py 中加入这一行并运行
        cursor.execute("SELECT primary_mission_objectives FROM satellites LIMIT 10")
        print(cursor.fetchall())
        # 获取 satellites 表的所有列信息
        cursor.execute("PRAGMA table_info(satellites)")
        columns = cursor.fetchall()
        print("=== 数据库表 'satellites' 的结构 ===")
        for col in columns:
            print(f"列 ID: {col[0]} | 列名: {col[1]} | 类型: {col[2]}")
    except Exception as e:
        print(f"❌ 查询出错: {e}")
    finally:
        conn.close()