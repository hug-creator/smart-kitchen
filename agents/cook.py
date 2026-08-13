"""烹饪 Agent：执行烹饪流程。

说明：烹饪是物理过程，不是 LLM 的强项，所以保持「模拟」——
真实项目里这里会对接厨电设备或机器人。用可配置的耗时模拟烹饪时长。
"""

import random
import time

from agents.common import KitchenState, log_step


def cook(state: KitchenState) -> KitchenState:
    t0 = time.time()

    state["log"].append(f"[烹饪] 开始料理 {state['dish']}...")

    # 模拟烹饪耗时（真实项目这里是对接设备）
    cook_time = random.uniform(0.5, 1.5)
    time.sleep(cook_time)

    state["cook_result"] = f"{state['dish']} 烹饪完成"
    log_step(state, "烹饪", f"{state['cook_result']}，耗时 {cook_time:.1f}s", t0)
    return state
