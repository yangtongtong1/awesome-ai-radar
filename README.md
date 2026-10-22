# Awesome AI Radar

一个每天自动更新的 GitHub AI 项目雷达，持续收集比较火、比较有趣、值得关注的 AI 仓库，并按主题分类和建立索引。

- 自动更新：每天北京时间约 08:00
- 数据来源：GitHub Repository Search API
- 收集范围：AI 模型、Agent、MCP、工具链、研究方向、数据集、生成式应用等
- 排名依据：Star 数、Fork 数、近期 Star 增长、最近更新时间与分类相关性

## 分类索引

总入口：[`INDEX.md`](./INDEX.md)

| 分类 | 关注点 |
|---|---|
| [Agents & MCP](./categories/agents-mcp.md) | AI Agent、工具调用、MCP、自动化工作流 |
| [LLM & RAG](./categories/llm-rag.md) | 大模型、推理、提示词、RAG、向量检索 |
| [Developer Tools](./categories/developer-tools.md) | 编码助手、CLI、IDE 插件、开发效率工具 |
| [Frameworks & Infrastructure](./categories/frameworks-infrastructure.md) | 训练、推理、部署、分布式与模型基础设施 |
| [Research & Papers](./categories/research-papers.md) | 论文实现、研究复现、技术综述 |
| [Data & Evaluation](./categories/data-evaluation.md) | 数据集、Benchmark、评测与安全 |
| [Vision, Audio & Creative](./categories/vision-audio-creative.md) | 图像、视频、语音、音乐、创意生成 |
| [Interesting Applications](./categories/interesting-applications.md) | 聊天机器人、自动化、WebUI、有趣的 AI 应用 |
| [Awesome & Guides](./categories/awesome-guides.md) | Awesome 列表、教程、学习路线与资源汇总 |
| [General AI & Machine Learning](./categories/general-ai-machine-learning.md) | 未归入以上主题的通用 AI / 机器学习项目 |

## 数据文件

- [`data/repos.json`](./data/repos.json)：当前入选仓库的结构化数据
- [`data/history.json`](./data/history.json)：每日 Star 快照，用于计算 7 天 / 30 天增长
- [`categories/`](./categories)：各分类详情页

## 自动更新机制

每日任务由 [`.github/workflows/collect.yml`](./.github/workflows/collect.yml) 触发：

1. 调用 GitHub Repository Search API 获取活跃 AI 仓库候选
2. 过滤 fork、归档、长期不更新和 Star 过低的项目
3. 按主题、名称和描述分类
4. 结合当前热度与历史 Star 增长计算分数
5. 重新生成 `INDEX.md`、分类页面和 JSON 数据
6. 如有变化，自动提交到 `main` 分支

分数是用于排序的启发式值，不是绝对质量评分。项目是否“有意思”仍建议结合描述和实际需求判断。

## 手动更新

在 GitHub 仓库页面进入 **Actions → Update AI Radar → Run workflow**，或使用 `workflow_dispatch` 触发一次立即更新。

## 说明

本项目只索引公开 GitHub 仓库元数据和链接，不复制第三方仓库内容。数据由 GitHub Actions 自动生成，可能出现分类误差或漏收；欢迎通过 Issue 提交建议。
