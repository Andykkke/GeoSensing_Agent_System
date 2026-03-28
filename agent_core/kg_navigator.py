import os
import json
from py2neo import Graph
from dotenv import load_dotenv

load_dotenv()


class KGNavigator:
    def __init__(self):
        # 初始化 Neo4j 连接
        self.graph = Graph(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
        )

        # 1. 定义资产类标签 (需在 StateManager 的 Asset_Summary 中进行数量比对)
        self.ASSET_TAGS = [
            "Boundary", "SatelliteTLE", "OverlapDict",
            "PlanningScheme", "SensorProfile", "EvaluationReport",
            "AssetInventory", "PlaceName"
        ]

    def get_eligible_tools(self, asset_summary: dict):
        """
        核心导航逻辑：
        1. 从图谱获取所有工具及其签名。
        2. 遍历工具，检查资产是否对齐。
        3. 元数据需求直接视为通过。
        """
        # 查询所有工具 (暂时剥离阶段过滤逻辑)
        query = """
        MATCH (t:GeoTool)
        RETURN t.tool_name AS name, 
               t.input_signature AS input_sig, 
               t.description AS desc,
               t.output_signature AS output_tag
        """
        all_tools = self.graph.run(query).data()

        eligible_tools = []

        for tool in all_tools:
            # 解析 input_signature (例如: '{"place_names": 1}' 或 '{"Boundary": 1}')
            try:
                # 注意：数据库存的是 JSON 字符串，需要解析为字典
                signature = json.loads(tool['input_sig'])
            except (json.JSONDecodeError, TypeError):
                print(f"警告: 工具 {tool['name']} 的签名格式错误")
                continue

            is_match = True

            # 遍历该工具的每一个输入需求
            for req_key, req_count in signature.items():

                # 逻辑分支 1: 如果需求属于“硬资产”
                # 注意：place_names 在 API 层面是元数据，但在逻辑层面由 PlaceName 资产支撑
                if req_key in self.ASSET_TAGS or req_key == "place_names":
                    # 映射关系：API 的 place_names 需求由资产 PlaceName 满足
                    check_tag = "PlaceName" if req_key == "place_names" else req_key

                    current_count = asset_summary.get(check_tag, 0)
                    if current_count < req_count:
                        is_match = False
                        break  # 资产不足，该工具出局

                # 逻辑分支 2: 如果需求属于“元数据” (如 mission_theme, sensor_type)
                else:
                    # 遵循“直通”原则：不检查 task_context，默认通过
                    continue

            if is_match:
                eligible_tools.append({
                    "name": tool['name'],
                    "description": tool['desc'],
                    "input_signature": signature,
                    "output_tag": tool['output_tag']
                })

        return eligible_tools


# 快速测试脚本
if __name__ == "__main__":
    # 模拟当前只有 PlaceName 资产的状态
    test_summary = {"PlaceName": 1}

    navigator = KGNavigator()
    tools = navigator.get_eligible_tools(test_summary)

    print(f"当前拥有资产: {test_summary}")
    print(f"解锁工具清单: {[t['name'] for t in tools]}")