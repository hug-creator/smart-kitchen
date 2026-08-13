"""质检 Agent：用 LLM 对菜品打分，决定通过/退回/降级。

升级点（相比 Day14 教学版）：
- 从「random 70/30」升级为「LLM 语义评分」
- 给出 1-10 分 + 具体文字反馈（"盐放多了""火候不够"）
- 分数 < 6 判定不通过，触发回路或降级
"""

import time

from agents.common import KitchenState, get_client, log_step, record_token, MODEL

QC_PROMPT = """你是餐厅质检员。刚做好的菜品是「{dish}」，请严格评分。

评分标准（1-10分）：
- 味道是否合适
- 火候/温度是否到位
- 卖相是否合格

6 分及以上为合格。只输出 JSON：
{{"score": 8, "feedback": "简短评价（10字以内）"}}"""

PASS_THRESHOLD = 6   # 低于 6 分不合格
MAX_RETRIES = 2      # 最多重做 2 次


def quality_check(state: KitchenState) -> KitchenState:
    t0 = time.time()
    state["qc_retries"] += 1

    client = get_client()
    try:
        import json
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": QC_PROMPT.format(dish=state["dish"])},
                {"role": "user", "content": state["cook_result"]},
            ],
            temperature=0.3,
        )
        record_token("质检", resp.usage)
        raw = resp.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removesuffix("```").strip()
        result = json.loads(raw)
        score = int(result.get("score", 0))
        feedback = result.get("feedback", "")
    except Exception as e:
        # 降级：LLM 不可用时随机打分
        import random
        score = random.randint(4, 9)
        feedback = f"（LLM 不可用，随机质检）{e}"
        log_step(state, "质检", f"LLM 质检失败，降级为随机评分", t0)

    state["qc_score"] = score
    state["qc_feedback"] = feedback
    state["qc_pass"] = score >= PASS_THRESHOLD

    if state["qc_pass"]:
        log_step(state, "质检", f"通过（{score}分）{feedback}", t0)
    elif state["qc_retries"] >= MAX_RETRIES:
        state["fallback"] = True
        log_step(state, "质检", f"第{state['qc_retries']}次不通过（{score}分）→ 触发降级", t0)
    else:
        log_step(state, "质检", f"第{state['qc_retries']}次不通过（{score}分）→ 退回重做 {feedback}", t0)

    return state
