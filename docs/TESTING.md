# Academic Writing Assistant 测试指南

这份文档用于验证文献规范整理、综述生成、导出文件和 DeepSeek 接入。建议每次修改格式核心后，先跑自动化测试，再用同一份测试论文走一遍浏览器流程。

## 1. 测试目标

重点检查以下结果：

1. 正文不会在整理或导出时丢失。
2. 参考文献数量、顺序和字段保持正确。
3. GB/T 7714、APA 7、IEEE 的输出互相独立。
4. Word、Markdown、TXT 的内容来源一致；TXT 包含完整正文，BibTeX、RIS、EndNote 只包含参考文献数据。
5. 期刊模板只影响排版，不会覆盖基础引用规范。
6. DeepSeek 只辅助识别参考文献字段，最终引用文本仍由本地渲染器生成。
7. DeepSeek 未配置、超时或返回错误时，本地规则仍能完成处理。

## 2. 固定测试数据

建立文件 `测试论文.md`，内容如下：

```markdown
# 测试论文

这是正文内容，用来确认整理和导出时正文不会丢失。

正文中的引用示例为 [1]，另一个引用为 [2]。

## 参考文献

Smith J, Lee K. Deep learning study. Nature, 2024, 35(2): 12-20. DOI: 10.1038/test1234.
Wang L. A method study. Science, 2023, 12(1): 30-40.
```

这份数据有意包含标题、正文、编号引用、卷期、页码和 DOI，足够覆盖当前格式核心的主要路径。

## 3. 自动化测试

在项目目录 `academic-writing-assistant` 中执行。Windows 推荐使用项目实际的 Python 路径：

```powershell
$env:DATA_DIR = "$PWD\.data-test"
Remove-Item -Recurse -Force $env:DATA_DIR -ErrorAction SilentlyContinue
& "C:\Users\wangxinyue\AppData\Local\Programs\Python\Python314\python.exe" -B -m unittest discover -s tests -q
```

通过标准是最后出现 `OK`。当前测试分工如下：

| 文件 | 覆盖内容 |
| --- | --- |
| `tests/test_core.py` | TXT/DOCX/PDF 解析、标题识别、参考文献解析、本地综述、SQLite 存储、Word 生成 |
| `tests/test_citation_engine.py` | GB/APA/IEEE 作者、年份、卷期、页码、DOI、排序和最终引用文本 |
| `tests/test_api.py` | 上传、历史记录、下载、引用检查、Word/TXT/BibTeX/RIS、异常输入和接口状态 |
| `tests/test_llm.py` | DeepSeek 兼容接口请求体、JSON 字段修正、未配置时跳过调用 |

不要把默认用户目录数据库用于测试。使用 `.data-test` 可以避免历史数据、权限和测试顺序互相影响。

## 4. 浏览器手工测试

### 4.1 启动和基础状态

```powershell
& "C:\Users\wangxinyue\AppData\Local\Programs\Python\Python314\python.exe" -B main.py
```

打开 `http://127.0.0.1:8765`，并确认：

- 页面可以加载；
- 文稿规范、综述生成、处理记录、期刊格式、统计看板标签可以切换；
- 文件选择框和开始按钮可以点击；
- 浏览器开发者工具 Console 没有 JavaScript 语法错误。

也可以检查接口：

```powershell
Invoke-WebRequest http://127.0.0.1:8765/api/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8765/api/llm-status -UseBasicParsing
```

### 4.2 文稿规范整理

1. 进入“文稿规范”。
2. 上传 `测试论文.md`。
3. 依次选择 GB/T 7714、APA 7、IEEE，分别点击“开始规整”。
4. 再选择一个期刊模板，例如 Nature 或 Science，重复一次。

每次结果都应满足：

- 标题存在；
- “这是正文内容”仍然存在；
- 参考文献数量为 2；
- 两条参考文献都存在；
- DOI `10.1038/test1234` 没有被删除；
- 选择期刊模板不会把基础规范错误替换成另一种规范；
- 页面布局和综述生成页面没有发生变化。

### 4.3 四种下载结果

对同一条整理记录分别下载：

| 下载格式 | 应包含 | 不应出现 |
| --- | --- | --- |
| Markdown | 标题、正文、参考文献 | 正文缺失 |
| TXT | 标题、正文、参考文献 | 只有参考文献 |
| Word | 完整文稿和排版 | 空白正文 |
| BibTeX/RIS/EndNote | 两条参考文献字段 | 把正文当成参考文献 |

TXT 是纯文本格式，不保存居中、字体和字号；标题左对齐属于正常现象。需要标题居中时检查 Word 文件。

### 4.4 综述生成回归测试

进入“综述生成”，上传两份或更多文献文件并点击生成。检查：

- 综述页面仍使用原来的界面；
- 文献卡片、关键词、比较结果正常显示；
- 没有配置 DeepSeek 时使用本地规则；
- 配置 DeepSeek 后只增强综述内容，不改变页面结构；
- 失败时显示错误状态，但仍能看到本地结果或可解释的失败提示。

### 4.5 历史记录和重新下载

1. 打开“处理记录”。
2. 找到刚才的整理记录。
3. 分别重新下载 Markdown、TXT 和 Word。
4. 刷新页面后再次下载。

刷新前后内容应一致，正文和参考文献都不能消失。

## 5. DeepSeek 测试

不要把 API Key 写进代码、README 或 Git。运行项目提供的安全启动脚本：

```powershell
.\start_deepseek.ps1
```

等出现隐藏输入提示后再粘贴 Key。启动后检查 `/api/llm-status`：

- `configured` 应为 `true`；
- `model` 应为 `deepseek-flash`；
- `api_url` 应为 DeepSeek chat completions 地址。

上传固定测试论文后检查：

- 参考文献字段可能被修正，但正文内容不被模型改写；
- 最终格式仍符合当前选择的 GB/APA/IEEE；
- API 返回非 JSON、超时或 401 时，页面仍能返回本地整理结果；
- 失败信息只显示状态，不显示 API Key。

因为 DeepSeek 调用会发送参考文献内容，包含未公开资料时应先确认数据合规性。测试结束后可关闭服务，或清除当前 PowerShell 会话中的 `LLM_API_KEY`。

## 6. 回归验收清单

每次格式核心修改后，至少确认：

- [ ] 自动化测试全部通过；
- [ ] 正文保留；
- [ ] 参考文献数量和顺序正确；
- [ ] 作者格式符合当前规范；
- [ ] 年份、卷号、期号、页码和 DOI 没有变成空字段；
- [ ] TXT 包含完整正文；
- [ ] Word 可以打开且标题、正文、参考文献均存在；
- [ ] 综述生成页面没有被改动；
- [ ] 历史记录可以重新下载；
- [ ] 未配置或调用失败时仍可使用本地规则；
- [ ] 没有把 API Key 写入文件或日志。

## 7. 问题记录模板

发现问题时记录以下信息，便于复现：

```text
测试日期：
输入文件：
选择的基础规范：GB/T 7714 / APA 7 / IEEE
选择的期刊模板：无 / Nature / Science / 其他
是否启用 DeepSeek：是 / 否
操作步骤：
实际结果：
预期结果：
涉及导出：页面 / Markdown / TXT / Word / BibTeX / RIS / EndNote
浏览器 Console 报错：
```
