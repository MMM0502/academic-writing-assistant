# 学术文稿智能处理系统

面向在校师生的轻量化学术写作工具，依据《基于大模型的学术文稿范式规整与文献综述智能生成系统》立项报告实现。

## 已实现的 MVP

- 单篇 `.docx`、`.pdf`、`.txt` 上传与文本提取
- GB/T 7714、APA 7、IEEE 三种参考文献格式规整
- 参考文献识别、编号重排、重复项提示和格式警告
- 多篇文献批量上传
- 基于规则与关键词聚类的结构化文献综述生成
- 可选的大模型增强模式（配置 OpenAI-compatible API 后自动启用）
- 结果下载为 Word 或 Markdown
- SQLite 历史记录
- 响应式网页端
- 20 条核心用户故事、OpenSpec change、自动化测试、CI 工作流

## 启动

```powershell
python main.py
```

浏览器访问 <http://127.0.0.1:8765>。

项目只依赖 Python 3.10+ 标准库即可运行。若需要更准确的 PDF 解析，可安装可选依赖：

```powershell
pip install -r requirements.txt
```

## 可选的大模型配置

系统默认使用本地规则引擎，不配置密钥也能完整演示。配置 API Key 后，综述生成会优先尝试调用 OpenAI-compatible 接口，接口失败时自动回退到本地引擎。`LLM_API_URL` 不填写时默认使用 OpenAI Chat Completions 地址：

```powershell
$env:OPENAI_API_KEY = "your-api-key"
$env:LLM_MODEL = "gpt-4o-mini"
python main.py
```

也可以使用项目原有变量名 `$env:LLM_API_KEY` 和 `$env:LLM_API_URL`。页面顶部的 AI 状态会显示当前是否已配置。

## 测试

```powershell
python -m unittest discover -s tests -v
```

## 目录结构

```text
app/
  formatters.py       文献格式规整与引用识别
  llm.py              可选大模型适配器
  parsers.py          DOCX/PDF/TXT 内容提取
  review.py           综述结构化生成
  storage.py          SQLite 持久化
  web.py              HTTP API 与静态资源服务
  static/             前端样式与交互
  templates/          主页面
docs/                 产品需求、架构和测试文档
openspec/             SDD 规格、设计与任务
tests/                单元测试
main.py               启动入口
```

## 注意

本版本输出用于辅助写作和教学演示。正式提交论文前，仍需由作者核对原文、引文、页码、DOI 和学术观点，避免把自动生成内容直接作为未经审核的研究结论。
