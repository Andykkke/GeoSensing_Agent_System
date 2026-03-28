import uuid
from typing import List, Dict, Any


class StateManager:
    """
    状态上下文管理器 (升级版)：维护 Agent 执行过程中的动态资产、任务背景与执行履历。
    """

    def __init__(self):
        # 1. 资产与背景的双轨存储 (原有)
        self.asset_registry: List[Dict[str, Any]] = []  # 数据资产列表
        self.task_context: Dict[str, Any] = {}  # 背景信息字典 (Metadata)

        # 2. 执行履历轨道 (新增：第三条轨道)
        # 存储格式: {"step_id": 1, "tool": "...", "thought": "...", "status": "Success", "output_tag": "..."}
        self.execution_history: List[Dict[str, Any]] = []

        # 3. 强对齐规范：标签与物理类型的唯一绑定表 (对齐本体 v2.0) [cite: 7, 9, 10]
        self.TYPE_MAPPING = {
            "Boundary": "GeoJSON_File",
            "SatelliteTLE": "Dict",
            "OverlapDict": "Dict",
            "PlanningScheme": "GeoJSON_File",
            "SensorProfile": "Dict",
            "EvaluationReport": "Dict",
            "AssetInventory": "List",
            "PlaceName": "String"
        }

    def initialize_from_intent(self, parsed_data: Dict[str, Any]):
        """
        接收 IntentParser 的输出并初始化系统状态。
        """
        # 注入背景信息
        self.task_context = parsed_data.get("task_metadata", {})

        # 注入初始资产 (如 PlaceName)
        initial_assets = parsed_data.get("initial_assets", [])
        for asset in initial_assets:
            self.add_asset(asset)

        print(f"系统初始化完成：目标任务阶段 -> {self.task_context.get('geo_task', {}).get('task_type')}")

    def add_asset(self, asset_info: Dict[str, Any]):
        """
        添加新资产：由执行模块(Executor)在 API 成功后调用。
        """
        tag = asset_info.get("semantic_tag")

        # 1. 强对齐校验 [cite: 7]
        expected_type = self.TYPE_MAPPING.get(tag)
        if expected_type and asset_info.get("data_type") != expected_type:
            raise TypeError(f"资产类型冲突：标签 {tag} 必须对应物理类型 {expected_type}")

        # 2. 维护 is_latest 逻辑：同标签的旧资产失效 [cite: 4]
        for asset in self.asset_registry:
            if asset["semantic_tag"] == tag:
                asset["is_latest"] = False

        # 3. 构造完整资产对象
        new_asset = {
            "data_id": asset_info.get("data_id", f"DATA_{uuid.uuid4().hex[:6].upper()}"),
            "semantic_tag": tag,
            "data_type": asset_info.get("data_type"),
            "value": asset_info.get("value"),
            "file_path": asset_info.get("file_path", ""),
            "is_latest": True,
            "desc": asset_info.get("desc", "")
        }
        self.asset_registry.append(new_asset)

    def record_step(self, snapshot: Dict[str, Any]):
        """
        记录执行履历 (新增)：由执行模块在 API 成功后，连同资产更新一起回传。
        """
        # 增加 step_id 自动管理或校验逻辑
        step_record = {
            "step_id": len(self.execution_history) + 1,
            "tool": snapshot.get("tool"),
            "thought": snapshot.get("thought"),
            "parameters": snapshot.get("parameters"),
            "output_tag": snapshot.get("output_tag"),
            "status": "Success"  # 只有成功的步骤才会被写入履历
        }
        self.execution_history.append(step_record)

    def get_asset_summary(self) -> Dict[str, int]:
        """
        为图谱导航器提供最新的资产计数表。
        """
        summary = {}
        for asset in self.asset_registry:
            if asset.get("is_latest"):
                tag = asset["semantic_tag"]
                summary[tag] = summary.get(tag, 0) + 1
        return summary

    def get_full_state_snapshot(self) -> Dict[str, Any]:
        """
        为决策模块提供完整的上下文快照。
        包含：所有最新资产、执行履历、以及任务目标。
        """
        return {
            "current_assets": [a for a in self.asset_registry if a["is_latest"]],
            "execution_history": self.execution_history,
            "task_goal": self.task_context.get("geo_task", {}).get("desc"),
            "target_phase": self.task_context.get("geo_task", {}).get("task_type")
        }

    def get_background_prompt(self) -> str:
        """
        为决策模块提取简明背景信息。
        """
        task = self.task_context.get("geo_task", {})
        event = self.task_context.get("disaster_event", {})
        return f"[任务目标]: {task.get('desc')} | [灾害背景]: {event.get('desc')}"