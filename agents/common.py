"""共享配置：LLM 客户端 + State 类型定义。

所有 Agent 从这里导入 State 和 LLM 客户端，避免循环依赖。
"""

import os
import time
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env（从项目根目录）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

_client = None


def get_client() -> OpenAI:
    """懒加载 LLM 客户端（单例）。"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


class KitchenState(TypedDict):
    """智能厨房全局状态 —— 所有 Agent 通过它通信。

    字段说明：
    - user_input: 客人原始输入
    - dish: 接单 Agent 解析出的菜品
    - quantity: 份数
    - inventory_ok: 库存是否充足
    - cook_result: 烹饪结果
    - qc_score: 质检分数(1-10)
    - qc_feedback: 质检文字反馈
    - qc_pass: 质检是否通过
    - qc_retries: 已重做次数
    - fallback: 是否触发降级
    - log: 全链路日志
    - timestamps: 各 Agent 耗时(ms)
    """
    user_input: str
    dish: str
    quantity: int
    inventory_ok: bool
    cook_result: str
    qc_score: int
    qc_feedback: str
    qc_pass: bool
    qc_retries: int
    fallback: bool
    log: list
    timestamps: dict


def log_step(state: KitchenState, agent: str, msg: str, t0: float) -> None:
    """统一日志记录：写入 log + 记录耗时。"""
    elapsed_ms = int((time.time() - t0) * 1000)
    state["log"].append(f"[{agent}] {msg} ({elapsed_ms}ms)")
    state["timestamps"][agent] = elapsed_ms
