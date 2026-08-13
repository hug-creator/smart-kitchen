"""接单 Agent：用 LLM 理解客人意图，解析出菜品和份数。

升级点（相比 Day14 教学版）：
- 从「关键字匹配」升级为「LLM 语义理解」
- 能理解"来碗热乎的蛋炒饭"、"刚才那个番茄炒蛋再来一份"这类自然语言
- 输出结构化 JSON：{"dish": 菜品名, "quantity": 份数}
"""

import json

from agents.common import KitchenState, get_client, log_step, MODEL
from db.database import list_dishes

PARSE_PROMPT = """你是餐厅点餐助手。从客人的话里提取「菜品名」和「份数」。

可选菜品：{dishes}

规则：
1. 菜品名必须是上面列表里的某一道（用相似度匹配，比如"番茄鸡蛋"→"番茄炒蛋"）
2. 份数默认 1，除非客人明确说"两份/再来一份"等
3. 如果听不出客人要点什么菜，dish 返回空字符串

只输出 JSON，格式：{{"dish": "菜品名", "quantity": 1}}"""


def accept_order(state: KitchenState) -> KitchenState:
    import time
    t0 = time.time()
    user_input = state["user_input"].strip()

    client = get_client()
    dishes = "、".join(list_dishes())

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PARSE_PROMPT.format(dishes=dishes)},
                {"role": "user", "content": user_input},
            ],
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        # 清理可能的 ```json 包裹
        raw = raw.removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(raw)
    except Exception as e:
        log_step(state, "接单", f"LLM 解析失败，降级为关键词匹配: {e}", t0)
        # 降级：关键词匹配
        parsed = _keyword_fallback(user_input, list_dishes())

    dish = parsed.get("dish", "")
    quantity = max(1, int(parsed.get("quantity", 1)))

    if not dish:
        state["dish"] = ""
        state["quantity"] = 0
        log_step(state, "接单", f"无法识别菜品，请客人重说", t0)
        return state

    state["dish"] = dish
    state["quantity"] = quantity
    log_step(state, "接单", f"识别：{dish} × {quantity}", t0)
    return state


def _keyword_fallback(user_input: str, dishes: list[str]) -> dict:
    """LLM 不可用时的兜底：简单关键词匹配。"""
    for dish in dishes:
        # 取菜品名核心字（去掉"炒""煎"等），做模糊匹配
        if dish in user_input or dish.replace("炒", "") in user_input:
            return {"dish": dish, "quantity": 1}
    return {"dish": "", "quantity": 0}
