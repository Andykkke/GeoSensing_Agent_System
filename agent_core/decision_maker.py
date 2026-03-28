import os
import json
import time  # 用于重试等待
from openai import OpenAI, RateLimitError  # 导入 RateLimitError 以便捕获
from typing import List, Dict, Any

class DecisionMaker:
    def __init__(self):
        """
        初始化决策模块。
        从环境变量加载 API 配置 。
        """
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.model = os.getenv("MODEL_NAME", "kimi-k2.5")

    def make_decision(self, eligible_tools: List[Dict], state_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据当前全态快照和合法工具清单做出决策，包含重试机制以应对 429 错误。
        输出格式：{ "action_params": {...}, "pending_snapshot": {...} } 。
        """
        # 1. 准备推理 Prompt
        prompt = self._build_decision_prompt(eligible_tools, state_snapshot)

        # 2. 带有指数退避的重试循环
        max_retries = 3
        retry_delay = 5  # 初始等待 5 秒

        for attempt in range(max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个地理空间任务规划专家，负责根据历史和现状决策下一步行动。"},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}  # 强制 JSON 输出 
                )

                # 3. 解析结果
                decision_raw = json.loads(completion.choices[0].message.content)
                
                # 4. 封装为“双部分”输出包给执行模块 
                return {
                    # 第一部分：用于执行 API 的物理参数
                    "action_params": {
                        "tool_name": decision_raw["selected_tool"],
                        "arguments": decision_raw["arguments"]
                    },
                    # 第二部分：准备给状态管理器的影子快照 (由 Executor 暂存)
                    "pending_snapshot": {
                        "tool": decision_raw["selected_tool"],
                        "thought": decision_raw["thought"],
                        "parameters": decision_raw["arguments"],
                        "output_tag": decision_raw["output_tag"]
                    }
                }

            except RateLimitError:
                # 捕获 429 错误并重试
                if attempt < max_retries - 1:
                    print(f"⚠️ [Decision] 服务器繁忙 (429)，将在 {retry_delay} 秒后进行第 {attempt + 2} 次重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数增加等待时间
                else:
                    print("❌ [Decision] 达到最大重试次数，服务器仍忙。请稍后再试或检查配额。")
                    raise
            except Exception as e:
                print(f"❌ [Decision] 决策模块发生未知错误: {str(e)}")
                raise

    def _build_decision_prompt(self, tools: List[Dict], snapshot: Dict[str, Any]) -> str:
        """
        构建深度推理 Prompt。
        集成了物理路径约束、执行履历反思和资产状态快照 。
        """
        # 提取由 main1.py 注入的物理环境参数
        env_db_path = snapshot.get("env_db_path", "未定义")

        # 格式化当前资产信息
        assets_str = "\n".join([
            f"- [{a['semantic_tag']}] ID: {a['data_id']}, Value/Path: {a['value'] or a['file_path']}"
            for a in snapshot["current_assets"]
        ])

        # 格式化执行履历 (赋予进展感，防止死循环) 
        history_str = "\n".join([
            f"Step {h['step_id']}: 使用 {h['tool']} -> 产出 {h['output_tag']} (Thought: {h['thought']})"
            for h in snapshot["execution_history"]
        ]) or "暂无执行记录"

        return f"""
        ### 0. 重要环境约束 (必须严格遵守)
        - 卫星数据库物理路径 (satellite_db_path): {env_db_path}
        - 如果调用 'get_satellite_tle'，必须包含 'satellite_db_path' 参数，值必须为上方给出的路径。

        ### 1. 任务目标
        目标阶段: {snapshot['target_phase']}
        任务描述: {snapshot['task_goal']}

        ### 2. 执行履历 (反思参考)
        {history_str}

        ### 3. 当前可用资产 (参数来源)
        {assets_str}

        ### 4. 候选工具清单 (图谱导航器初筛)
        {json.dumps(tools, ensure_ascii=False, indent=2)}

        ### 决策要求：
        1. **逻辑排重**：检查执行履历，严禁重复调用已成功产出最新资产的工具 。
        2. **参数对齐**：根据工具的 input_signature，从“当前可用资产”中提取具体的 value 或 file_path 填充到 arguments 中。
        3. **产出预判**：明确该工具执行后将产出的 semantic_tag（参考候选工具的 output_tag）。

        ### 请输出标准 JSON 格式：
        {{
          "selected_tool": "工具名",
          "thought": "基于进展感和资产现状的推理逻辑",
          "output_tag": "预期产出的标签",
          "arguments": {{ "API参数名": "对应资产值" }}
        }}
        """
