# 学术文稿智能处理系统

面向在校师生的轻量化学术写作工具，依据《基于大模型的学术文稿范式规整与文献综述智能生成系统》立项报告实现。

## 已实现的功能

- 单篇 `.docx`、`.pdf`、`.txt`、`.md` 上传与文本提取
- GB/T 7714、APA 7、IEEE 三种参考文献格式规整
- 参考文献结构化解析：作者、年份、题名、来源、卷号、期号、页码、DOI、URL、文献类型、解析置信度
- 参考文献识别、编号重排、重复项提示、年份缺失提示、低置信度提示
- 正文引用交叉检查：识别 `[1]`、`[1-3]`、`(作者, 年份)` 等引用，比对参考文献列表，发现孤立引用、未引用文献、重复编号和编号不连续
- 多篇文献批量上传
- 基于规则与关键词聚类的结构化文献综述生成
- 可选的大模型增强模式（配置 OpenAI-compatible API 后自动启用，失败回退本地引擎）
- 规整版 Word 导出：统一字体、字号、行距、首行缩进，参考文献悬挂缩进，编号连续，参考文献章节只出现一次
- 结果下载为 Word 或 Markdown
- SQLite 历史记录，支持单条删除和清空
- 响应式网页端
- 自动化单元测试与端到端接口测试、CI 工作流

## 启动

默认数据目录位于用户主目录下 `~/.academic-assistant`，普通用户权限即可写入。

Windows：

```powershell
py main.py
```

Linux / macOS：

```bash
python3 main.py
```

浏览器访问 <http://127.0.0.1:8765>。

项目只依赖 Python 3.10+ 标准库即可运行。若需要更准确的 PDF 解析，可安装可选依赖：

```powershell
pip install -r requirements.txt
```

### 自定义数据目录

通过环境变量 `DATA_DIR` 指定一个可写的目录，数据库将保存在其中：

```powershell
$env:DATA_DIR = "D:\my-academic-data"
py main.py
```

```bash
export DATA_DIR=/var/lib/academic-assistant
python3 main.py
```

## 可选的大模型配置

系统默认使用本地规则引擎，不配置密钥也能完整演示。配置以下环境变量后，综述生成会优先尝试调用 OpenAI-compatible 接口，接口失败时自动回退到本地引擎：

```powershell
$env:LLM_API_KEY = "your-api-key"
$env:LLM_API_URL = "https://api.openai.com/v1/chat/completions"
$env:LLM_MODEL = "gpt-4o-mini"
py main.py
```

## 测试

```powershell
py -m unittest discover -s tests -v
```

## API 接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET | `/api/rules` | 获取引用规范与文献类型列表 |
| GET | `/api/history` | 获取历史记录列表 |
| GET | `/api/history/{id}` | 获取单条记录详情 |
| DELETE | `/api/history/{id}` | 删除单条记录 |
| DELETE | `/api/history` | 清空全部记录 |
| POST | `/api/format` | 单篇文稿规整 |
| POST | `/api/review` | 批量文献综述生成 |
| POST | `/api/check-citations` | 正文引用交叉检查 |
| GET | `/api/download/{id}?format=docx` | 下载规整版 Word |
| GET | `/api/download/{id}?format=md` | 下载 Markdown |

## 目录结构

```text
app/
  config.py           配置与数据目录管理
  formatters.py       文献结构化解析、格式规整、引用交叉检查
  llm.py              可选大模型适配器
  parsers.py          DOCX/PDF/TXT 内容提取
  review.py           综述结构化生成
  exporters.py        规整版 Word 与 Markdown 导出
  storage.py          SQLite 持久化
  web.py              HTTP API 与静态资源服务
  static/             前端样式与交互
  templates/          主页面
docs/                 产品需求、架构和测试文档
openspec/             SDD 规格、设计与任务
tests/                单元测试与端到端接口测试
main.py               启动入口
```

## 注意

本版本输出用于辅助写作和教学演示。正式提交论文前，仍需由作者核对原文、引文、页码、DOI 和学术观点，避免把自动生成内容直接作为未经审核的研究结论。
