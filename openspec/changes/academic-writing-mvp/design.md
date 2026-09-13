# Design

## 模块

- `parsers.py`：统一文件到文本的输入边界，DOCX 使用 ZIP/XML，PDF 使用可选 pypdf，TXT 使用 UTF-8。
- `formatters.py`：识别参考文献、抽取作者/标题/年份/来源、根据规范生成结果并记录风险。
- `review.py`：按关键词建立轻量主题分组，生成结构化 Markdown；通过 `llm.py` 可选增强。
- `storage.py`：SQLite 记录处理结果，原始上传文件不落盘。
- `web.py`：标准库 HTTP 服务、multipart 解析、JSON API 和静态资源服务。

## 数据流

1. 浏览器提交 multipart/form-data。
2. Web 层限制大小并清理文件名。
3. Parser 提取文本。
4. 业务引擎生成结果。
5. Store 保存结果。
6. Web 层返回 JSON，前端渲染并提供下载。

## 关键决策

MVP 仅依赖 Python 标准库，保证教学环境开箱可运行。`pypdf` 作为可选增强依赖；LLM 为可插拔适配器，调用失败时本地引擎兜底。
