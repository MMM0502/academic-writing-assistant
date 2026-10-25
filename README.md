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

使用 DeepSeek 时，可在 PowerShell 运行 `.\start_deepseek.ps1`，并在隐藏输入提示中粘贴 API Key。该配置用于综述生成和文献字段识别；文献最终格式仍由本地 GB/APA/IEEE 渲染器生成。上传文稿中的参考文献条目会发送到所配置的模型服务。
## 学校论文模板搜索

首页 `01 学校格式推荐` 支持按「学历 → 学校 → 学院」定位论文模板，按顺序回退：

1. **本地模板库** —— 已入库（人工确认或历史检索）的来源直接命中，不联网；
2. **查询缓存** —— 归一化后的（学历, 学校, 学院）命中缓存，正向结果存 30 天、负向结果存 24 小时，避免重复调用付费接口；
3. **Tavily 联网检索** —— 结果按教育机构域名与标题相关度排序后写入 `school_templates`，状态为“待人工核验”，不会自动认定为学校官方最新版本；
4. **兜底** —— 仍无结果时提示改用 `05 期刊格式` 的自定义格式。

搜索 Key 由**部署者**通过环境变量配置一次，普通使用者不需要填写：

```powershell
$env:TAVILY_API_KEY = "tvly-..."
py main.py
```

希望每次启动都生效，可写入当前用户环境变量（明文保存在用户注册表，注意不要提交到仓库）：

```powershell
[Environment]::SetEnvironmentVariable("TAVILY_API_KEY", "tvly-...", "User")
# 新开的终端才会继承；已经开着的终端需要重新打开或手动 $env:TAVILY_API_KEY
```

未配置时启动日志会打印提示，页面显示“检索服务未启用”，本地格式推荐、文稿规整与自定义期刊格式均不受影响。可通过 `TAVILY_API_URL` 覆盖默认搜索接口。候选来源及检索摘要保存在 `school_templates` 表中；网页日期和教育域名仅作线索，使用前仍需打开来源核对发布部门、适用学院/学历和版本。

## 测试

```powershell
py -m unittest discover -s tests -v
```

完整的自动化、浏览器、导出和 DeepSeek 测试步骤见 [docs/TESTING.md](docs/TESTING.md)。

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
