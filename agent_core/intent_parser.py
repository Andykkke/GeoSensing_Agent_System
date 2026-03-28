import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class IntentParser:
    """
    意图解析器：将自然语言需求转化为系统初始化协议。
    逻辑分区：数据资产区 (Data Assets) 与 背景信息区 (Metadata)。
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.model = os.getenv("MODEL_NAME", "kimi-k2.5")

    def parse_intent(self, user_query: str) -> dict:
        """解析用户指令"""
        system_prompt = self._generate_parsing_prompt()

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            response_format={"type": "json_object"}  # 强制 JSON 输出
        )

        raw_result = completion.choices[0].message.content
        return json.loads(raw_result)

    def _generate_parsing_prompt(self) -> str:
        """构建解析逻辑 Prompt"""
        return """
        你是一个地理空间任务专家。你的任务是解析用户的自然语言指令，并将其转化为结构化的 JSON 初始化协议。

        ### 必须遵守的逻辑分区：
        1. **initial_assets (数据资产区)**：
           - 提取需求中的地理位置实体。
           - 格式：{"semantic_tag": "PlaceName", "value": "...", "data_type": "String", "data_id": "INIT_LOC_001"}
           - 理由：这些资产会进入 Asset_Registry，参与图谱导航器的 input_signature 硬过滤。

        2. **task_metadata (背景信息区)**：
           - **geo_task**：包含 task_type（必须是 Discovery, Evaluation, Configuration 之一 [cite: 1, 3]）和任务描述 desc。
           - **disaster_event**：包含 event_type 和情境描述 desc。
           - 理由：这些信息进入 Task_Context，仅作为决策模块生成 Thought 时的上下文，不参与工具筛选。

        ### 约束条件：
        - 严禁模糊匹配。
        - 必须返回标准 JSON 格式。

        ### 示例输出：
        {
          "initial_assets": [
            { "data_id": "INIT_LOC_001", "semantic_tag": "PlaceName", "value": "武汉", "data_type": "String" }
          ],
          "task_metadata": {
            "geo_task": { "task_type": "Configuration", "desc": "规划武汉洪涝观测方案" },
            "disaster_event": { "event_type": "Flood", "desc": "武汉市遭遇持续强降雨，城区积水" }
          }
        }
        """


# 单元测试逻辑
if __name__ == "__main__":
    parser = IntentParser()
    test_query = "我需要一个能在2025年7月1日观测成都地区云量的单星光学观测方案，要求覆盖率大于80%。"
    result = parser.parse_intent(test_query)
    print(json.dumps(result, indent=2, ensure_ascii=False))