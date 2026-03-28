import requests
import json
import os

# 配置信息
BASE_URL = "http://127.0.0.1:8000"
DATA_DIR = r"E:\GeoSensing_Agent_System\data"
DB_PATH = os.path.join(DATA_DIR, "databases", "satellite_data.db")


def verify_full_workflow():
    print("=== GeoSensing API 物理层全流程验证 ===\n")

    # --- Step 1: 获取行政边界 (Discovery) ---
    print("[Step 1] 调用 /get_boundary 获取成都边界...")
    # 注意：get_boundary 接收地名字符串
    boundary_payload = {"place_names": "Chengdu"}
    res1 = requests.post(f"{BASE_URL}/get_boundary", json=boundary_payload)
    if res1.status_code != 200:
        print(f"❌ Step 1 失败: {res1.text}")
        return

    # 物理工具 getPlaceBoundary 会保存文件并返回路径
    boundary_path = res1.json().get("data")
    print(f"    ✅ 成功获取边界路径: {boundary_path}")

    # --- Step 2: 查询卫星 TLE (Discovery) ---
    # --- Step 2: 查询卫星 TLE (Discovery) ---
    print("\n[Step 2] 调用 /get_satellite_tle 查询卫星...")

    # 确保路径包含 databases 文件夹
    DB_PATH = os.path.join(DATA_DIR, "databases", "satellite_data.db")

    tle_payload = {
        "satellite_db_path": DB_PATH,
        # 修改点：将 "Flood" 改为数据库中存在的 "Cloud cover"
        "mission_theme": "Cloud cover",
        # 修改点：将 "Optical Sensor" 简写为 "Optical" (配合下方的 LIKE 模糊匹配)
        "sensor_type": "Optical"
    }
    res2 = requests.post(f"{BASE_URL}/get_satellite_tle", json=tle_payload)
    if res2.status_code != 200 or not res2.json().get("success"):
        print(f"❌ Step 2 失败: {res2.text}")
        return

    tle_dict = res2.json().get("data")
    print(f"    ✅ 成功获取 {len(tle_dict)} 颗卫星的 TLE 数据")

    # --- Step 3: 计算观测重叠率 (Query/Discovery) ---
    print("\n[Step 3] 调用 /get_observation_overlap 计算覆盖详情...")
    overlap_payload = {
        "tle_dict": tle_dict,
        "start_time_str": "2025-07-01 00:00:00.000",
        "end_time_str": "2025-07-01 23:59:59.000",
        "target_geojson_path": boundary_path,
        # 【修改点 1】: 将 10.0 改为 60.0，增加覆盖范围
        "fov": 60.0,
        # 采样间隔 600 秒
        "interval_seconds": 600
    }
    res3 = requests.post(f"{BASE_URL}/get_observation_overlap", json=overlap_payload)
    if res3.status_code != 200 or not res3.json().get("success"):
        print(f"❌ Step 3 失败: {res3.text}")
        return

    coverage_results = res3.json().get("coverage_results")
    print(f"    ✅ 成功计算重叠率，共有 {len(coverage_results)} 颗卫星有覆盖记录")

    # --- Step 4: 规划最优方案 (Configuration) ---
    print("\n[Step 4] 调用 /plan_satellite_combination 生成最终方案...")
    plan_payload = {
        "coverage_results": coverage_results,
        "target_geojson_path": boundary_path,
        "target_coverage": 0.8  # 对应论文要求 >80%
    }
    res4 = requests.post(f"{BASE_URL}/plan_satellite_combination", json=plan_payload)
    if res4.status_code != 200 or not res4.json().get("success"):
        print(f"❌ Step 4 失败: {res4.text}")
        return

    final_plan = res4.json()
    print("\n" + "=" * 50)
    print("【物理层验证成功 - 最终方案摘要】")
    print(f"- 是否达标: {final_plan.get('meets_target')}")
    print(f"- 总覆盖率: {final_plan.get('total_coverage_percentage'):.2f}%")
    print(f"- 选定卫星: {final_plan.get('satellite_names')}")
    print(f"- 方案文件: {final_plan.get('covered_geojson_path')}")
    print("=" * 50)


if __name__ == "__main__":
    verify_full_workflow()