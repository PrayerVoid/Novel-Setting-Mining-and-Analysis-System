import json
import random
from typing import Dict, Any
from zhipuai import ZhipuAI

class AIService:
    """
    AI 服务，对接智谱 GLM-4.5-Flash。
    """
    def __init__(self):
        # API Key Pool (轮换池)
        self.api_keys = [
            "1e8cae721103416a8e4cd7e9f4366285.Yezgeb3ybThYmHqV",
            "c90fb13295234851aeee5a44eae6d650.t0CaxOWUg5guSXPz",
            "595876ef8347467585f50f43af419ad9.2dtMBnRS0swoDBvR",
        ]
        # 随机选择起始索引，后续按轮换(next)策略切换
        self.current_key_index = random.randrange(len(self.api_keys))
        self.model = "glm-4.5-flash"

    def get_client(self):
        # 使用当前索引对应的 key（轮换池）
        return ZhipuAI(api_key=self.api_keys[self.current_key_index])

    def rotate_key(self):
        """将当前 API key 切换到下一个（循环）并返回新的 key"""
        old = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        # 仅打印 key 的前几位以便调试，避免泄露全部 key
        print(f"  [AIService] Rotate API key: {old} -> {self.current_key_index}, new key prefix: {self.api_keys[self.current_key_index][:8]}...")
        return self.api_keys[self.current_key_index]

    def _is_concurrency_error(self, exc: Exception) -> bool:
        """粗略识别并发限制错误（例如：429 / 1305 / '当前API请求过多'）"""
        text = str(exc)
        return ('1305' in text) or ('当前API请求过多' in text) or ('Error code: 429' in text)

    def extract_settings_from_text(self, chapter_content: str, existing_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        从文本中提取设定。
        """
        print(f"  [AIService] 分析章节内容 ({len(chapter_content)} 字符)...")
        
        # 构造 Prompt
        # 简化已有设定以节省 Token (仅保留名称和类型，或者关键属性)
        # 这里直接传入完整 JSON，如果太大可能需要截断或摘要
        existing_json = json.dumps(existing_settings, ensure_ascii=False)
        
        prompt = f"""
你是一位资深的小说设定分析师和知识图谱专家。你的任务是根据“已有设定”和“新章节内容”，增量更新世界观设定。

### 核心原则
1.  **去冗余**: 仅提取对剧情有长期影响的**核心实体**（主要角色、主要势力、关键地点）。忽略路人、杂兵、一次性物品、普通数值（如伤害值）。
2.  **实体类型限制**: 建议使用常见类型以降低类型的复杂度，鼓励使用以下类型：
    *   `人物`: 现实中的重要角色。
    *   `组织`: 宗门、帮派、公司、国家。
    *   `地点`: 城市、秘境、重要场所。
    *   `宝物`: 具有唯一名字且推动剧情的传说级宝物（普通装备作为属性）。
    *   **注意**: `技能`,`功法`,`装备`,`境界`等**绝对不要**作为独立实体，必须作为某个实体的属性。
3.  **属性转关系**:
    *   如果某属性的值是另一个实体（或疑似实体），**必须**将其转化为关系，而不是保留在属性 中。
    *   例如：不要 `{{ "name": "小王", "properties": {{ "老师": "小红" }} }}`，要生成关系 `{{ "subject": "小王", "object": "小红", "relation": "教师" }}`。
4.  **别名归集**: 实体的所有外号、头衔、曾用名，统一放入属性中的 `别名` 字段，用逗号分隔。
5.  **实体去重与合并**:
    *   **严格检查**“已有设定”中是否存在同指实体。
    *   例如：如果已有实体“《零》”，新章节出现“《零》游戏”，这显然是同一个事物。**绝对不要**创建新实体“《零》游戏”。
    *   操作：将“《零》游戏”作为别名添加到“《零》”的 `别名` 属性中，并将新属性更新到“《零》”下。
6.  **属性更新与归一 (Update & Unify Properties)**:
    *   当新章节内容更新了某个实体的现有属性时（例如，等级、经验值、金钱），**必须**更新旧属性的值，而不是创建新的相似属性。
    *   例如：如果已有属性 `{{ "等级": 10 }}`，新内容显示角色升到了11级，应更新为 `{{ "等级": 11 }}`，**绝对不要**添加新属性如 `{{ "级别": 11 }}`。
    *   与已有属性的名称、内容结构都接近（如`{{攻击:5}}`和`{{攻击力:6}}`）的新属性，应识别为同一属性的更新，统一为一个标准属性名，然后更新其值。

### 输入数据
1. **已有设定**:
{existing_json}

2. **新章节内容**:
{chapter_content}

### 输出格式 (严格 JSON)
请直接返回 JSON 数据，不要包含 Markdown 代码块标记（如 ```json）。
**严禁在 JSON 中包含注释（如 // 或 /* ... */），否则会导致解析失败。**
格式如下：
{{
  "new_settings": {{
    "entities": [
      {{ 
        "name": "实体名", 
        "type": "类型", 
        "properties": {{ 
          "别名": "别名1, 别名2", 
          "别名": "技能列表",
          "装备": "装备列表",
          "属性名": "属性值" 
        }} 
      }}
    ],
    "relationships": [
      {{ "subject": "主体名", "object": "客体名", "relation": "关系名" }}
    ]
  }},
  "invalidated_settings": [
      {{ "type": "relationship", "subject": "主体名", "object": "客体名", "relation": "关系名" }},
      {{ "type": "property", "entity": "实体名", "key": "属性名" }}
  ]
}}
"""
        # 尝试调用，遇到并发限制时切换 API key 并重试一次
        try:
            response = self.get_client().chat.completions.create(
                model=self.model,
                thinking={"type":"disabled"},
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1, # 低温度以保证输出格式稳定
                top_p=0.7,
            )
        except Exception as e:
            print(f"  [AIService] 调用失败: {e}")
            if self._is_concurrency_error(e):
                print("  [AIService] 并发错误，切换 API Key 并重试一次。")
                self.rotate_key()
                try:
                    response = self.get_client().chat.completions.create(
                        model=self.model,
                        thinking={"type":"disabled"},
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        top_p=0.7,
                    )
                except Exception as e2:
                    print(f"  [AIService] 重试失败: {e2}")
                    raise Exception(f"AI API调用失败，提取终止: {str(e2)}")
            else:
                # 非并发错误直接抛出
                raise Exception(f"AI API调用失败，提取终止: {str(e)}")

        content = response.choices[0].message.content
        print(f"  [AIService] Raw Response: {content}") # Debug print
        
        # 清理可能的 Markdown 标记
        content = content.replace("```json", "").replace("```", "").strip()
        
        # 尝试清理注释 (简单的行级清理，防止 AI 还是输出了注释)
        import re
        # 移除 // 及其后的内容，但要小心 URL (http://...)
        # 简单起见，只移除行首或空白后的 //
        content = re.sub(r'\s*//.*', '', content)
        
        result = json.loads(content)
        print("  [AIService] 分析完成。")
        return result

    def detect_conflicts(self, previous_settings: Dict[str, Any], chapter_content: str) -> Dict[str, Any]:
        """
        检测本章内容与已有设定之间的冲突。
        """
        existing_json = json.dumps(previous_settings, ensure_ascii=False)
        
        prompt = f"""
你是一个严谨的小说逻辑检查员。你的任务是检查“新章节内容”是否与“已有设定”存在逻辑冲突。

### 任务说明
1.  仔细阅读“已有设定”和“新章节内容”。
2.  找出新章节中与已有设定**直接矛盾**的地方。
    *   例如：设定中某人已死，新章节中却活着出现。
    *   例如：设定中某人是女性，新章节中被称为“他”。
    *   例如：设定中某地在东方，新章节中却说在西方。
3.  忽略有铺垫的设定变更（如等级提升、关系变化），只关注**明显的逻辑错误**，只有完全无法解释的矛盾才被认为是冲突。
4.  如果发现冲突，提取出新章节中的**原文片段**，并指出冲突的**具体设定**以及该设定**最早出现的章节**。
    *   请从“已有设定”JSON中查找对应的 `start_chapter` (实体/关系) 或 `property_start_chapters` (属性)。

### 输入数据
1. **已有设定**:
{existing_json}

2. **新章节内容**:
{chapter_content}

### 输出格式 (严格 JSON)
{{
  "conflicts": [
    {{
      "original_text": "新章节中存在冲突的原文片段",
      "conflicting_setting": "已有设定中对应的描述 (例如: '张三: 等级=10')",
      "start_chapter": 1,  // 该设定最早出现的章节号 (整数)
      "description": "简要说明冲突原因"
    }}
  ]
}}
如果未发现冲突，返回 {{ "conflicts": [] }}。
"""
        try:
            response = self.get_client().chat.completions.create(
                model=self.model,
                thinking={"type":"disabled"},
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
        except Exception as e:
            print(f"  [AIService] Conflict Detection Error: {e}")
            if self._is_concurrency_error(e):
                print("  [AIService] 并发错误，切换 API Key 并重试一次。")
                self.rotate_key()
                try:
                    response = self.get_client().chat.completions.create(
                        model=self.model,
                        thinking={"type":"disabled"},
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                    )
                except Exception as e2:
                    print(f"  [AIService] Conflict Detection 重试失败: {e2}")
                    return {"conflicts": [], "error": str(e2)}
            else:
                return {"conflicts": [], "error": str(e)}

        content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)

    def chat_with_context(self, previous_settings: Dict[str, Any], chapter_content: str, user_query: str) -> str:
        """
        基于设定和章节内容的 AI 对话。
        """
        existing_json = json.dumps(previous_settings, ensure_ascii=False)
        
        system_prompt = f"""
你是一个熟悉该小说剧情的 AI 助手。你拥有以下背景知识：

1.  **截止上一章的世界观设定**:
{existing_json}

2.  **当前章节内容**:
{chapter_content}

请基于以上信息回答用户的问题。如果信息不足，请如实告知。回答要简洁明了。
"""
        try:
            response = self.get_client().chat.completions.create(
                model=self.model,
                thinking={"type":"disabled"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.7,
            )
        except Exception as e:
            if self._is_concurrency_error(e):
                print(f"  [AIService] chat 调用并发错误: {e} ，切换 API Key 并重试一次。")
                self.rotate_key()
                try:
                    response = self.get_client().chat.completions.create(
                        model=self.model,
                        thinking={"type":"disabled"},
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ],
                        temperature=0.7,
                    )
                except Exception as e2:
                    return f"AI 响应出错: {str(e2)}"
            else:
                return f"AI 响应出错: {str(e)}"

        return response.choices[0].message.content

# 单例实例
ai_service = AIService()
