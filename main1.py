import time
from agent_core.intent_parser import IntentParser
from agent_core.state_manager import StateManager
from agent_core.kg_navigator import KGNavigator
from agent_core.decision_maker import DecisionMaker
from agent_core.executor import Executor


def run_geosensing_agent(user_query: str):
    # 1. 初始化所有模块
    parser = IntentParser()
    state_manager = StateManager()
    navigator = KGNavigator()
    decision_maker = DecisionMaker()
    executor = Executor(state_manager)

    # 2. 意图解析与状态初始化
    print("\n[Step 0] 意图解析中...")
    intent_protocol = parser.parse_intent(user_query)
    state_manager.initialize_from_intent(intent_protocol)

    # 3. 启动 ReAct 循环
    max_iterations = 5
    for i in range(max_iterations):
        print(f"\n--- 🔄 第 {i + 1} 轮推理循环 ---")

        # A. 图谱导航：硬过滤合法工具
        asset_sum = state_manager.get_asset_summary()
        eligible_tools = navigator.get_eligible_tools(asset_sum)

        # B. 决策模块：逻辑择优与参数填充
        # --- [核心修改点] ---
        full_snapshot = state_manager.get_full_state_snapshot()
        # 物理层对齐：将 executor 模块中定义的 db_path 注入快照，
        # 否则 DecisionMaker 无法得知数据库在磁盘的具体位置
        full_snapshot["env_db_path"] = executor.db_path

        print(f"🧠 [Main] 正在决策中... (已注入数据库路径: {executor.db_path})")

        # 调用决策模块生成指令包
        decision = decision_maker.make_decision(eligible_tools, full_snapshot)

        # C. 执行模块
        # 执行成功不仅意味着 HTTP 200，还意味着业务 success 为 True
        success = executor.execute(decision["action_params"], decision["pending_snapshot"])

        if not success:
            print(f"❌ 业务逻辑执行失败（如：未找到卫星），停止任务。")
            break

        # D. 终止判定：深度检查
        if decision["pending_snapshot"]["output_tag"] == "PlanningScheme":
            # 获取刚刚存入的最新资产
            latest_plan = \
            [a for a in state_manager.asset_registry if a["semantic_tag"] == "PlanningScheme" and a["is_latest"]][0]

            # 检查规划结果是否真正有效
            plan_content = latest_plan.get("value")
            if plan_content and plan_content.get("success") and plan_content.get("meets_target"):
                print(f"\n🎯 任务完美达成！覆盖率: {plan_content.get('total_coverage_percentage')}%")
            else:
                print(f"\n⚠️ 任务虽结束但未达标: {plan_content.get('message') if plan_content else '未知错误'}")
            break

        time.sleep(1)  # 模拟思考间隔


if __name__ == "__main__":
    query = "2025 年 7 月初，成都市遭遇极端强降雨过程，岷江、沱江流域水位暴涨，多个中心城区出现严重内涝。为了实时掌握受灾范围及水体演变趋势，指挥部需要紧急规划卫星观测任务 。我需要一个能在2025年7月1日观测成都地区云量的单星光学观测方案，要求覆盖率大于80%。"
    run_geosensing_agent(query)