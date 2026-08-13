# 智能餐厅多智能体系统（Smart Kitchen）

基于 LangGraph 构建的 4 智能体协作系统，实现从「客人自然语言点餐」到「菜品上桌」的完整闭环。

## ✨ 核心亮点

- **多智能体协作**：接单 / 库存 / 烹饪 / 质检 4 个 Agent 各司其职，通过 LangGraph StateGraph 编排
- **LLM 语义理解**：接单用 LLM 解析自然语言（"来碗热乎的蛋炒饭"），质检用 LLM 打分（1-10 分 + 文字反馈）
- **真实持久化**：库存使用 SQLite，下单真实扣减、降级真实回滚，重启不丢数据
- **失败恢复**：质检不合格自动退回重做（回路），连续失败触发优雅降级（回滚库存 + 友好提示）
- **全链路可观测**：每个 Agent 的耗时、日志、库存快照实时展示，黑盒变白盒
- **产品级界面**：Element UI 风格，4 个 Tab（实时下单 / 库存管理 / 订单历史 / 系统监控）

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 .env（填入 DeepSeek API Key）
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=sk-xxx

# 3. 运行
python main.py
# 打开 http://127.0.0.1:5000
```

## 🖥 界面预览

| 实时下单 | 库存管理 | 订单历史 | 系统监控 |
|---|---|---|---|
| 自然语言点餐 + 流程时间轴 | 库存表格 + 状态预警 | 订单记录 + 质检分 | 统计大卡 + 架构图 |

## 📁 项目结构

```
smart-kitchen/
├── agents/                  # 4 个 Agent 模块
│   ├── common.py            #   LLM 客户端 + State 定义
│   ├── accept_order.py      #   接单（LLM 解析意图）
│   ├── inventory.py         #   库存（SQLite 扣减）
│   ├── cook.py              #   烹饪（模拟）
│   ├── quality_check.py     #   质检（LLM 评分）
│   └── fallback.py          #   降级 + 上菜
├── db/
│   └── database.py          # SQLite 持久化层
├── frontend/
│   ├── templates/index.html # Element UI 界面
│   └── static/              # CSS + JS
├── docs/                    # 架构文档 + 图
├── tests/                   # pytest 测试用例
├── main.py                  # Flask + LangGraph 编排
├── requirements.txt
└── pytest.ini
```

## 🧪 运行测试

```bash
pytest -v
```

## 🏗 技术栈

| 层 | 技术 |
|---|---|
| 编排框架 | LangGraph（StateGraph / 条件边 / 回路） |
| LLM | DeepSeek（OpenAI 兼容接口） |
| 后端 | Flask + Flask-CORS |
| 持久化 | SQLite |
| 前端 | 原生 HTML/CSS/JS（Element UI 风格） |
| 测试 | pytest |

## 🎯 设计决策

1. **为什么用 LangGraph 不用 LangChain？** 质检失败需要「退回重做」的回路，LangChain 的 Chain 只能往前走。
2. **质检失败为什么退回烹饪而不是重新规划？** 内容问题重做即可，不需要重新解析订单。
3. **降级策略如何设计？** 连续 2 次质检失败 → 回滚库存 + 友好提示，不让系统崩溃。

## 📚 文档

- [架构设计文档](docs/architecture.md)
- [数据库 ER 图](docs/数据库ER图.html)
- [Agent 协作泳道图](docs/Agent协作泳道图.html)
- [系统运行全流程图](docs/系统运行全流程图.html)
