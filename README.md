# Intelligent Industry Analyst Framework

多Agent协作的智能行业分析系统，支持微信公众号实时数据爬取，通过优化设计最大化节省token使用。

## 核心特性

- **5个专业Agent协作**：从需求分析到报告生成的完整流程
- **交互式工作流** 🆕：Planner生成计划后用户可确认/修改，Researcher生成检索策略后用户可确认/修改
- **多数据源支持** 🆕：
  - 微信公众号爬取（指定公众号实时获取资讯）
  - Twitter/X 账号爬取（支持时间过滤和关键词筛选）
  - Claude Web Search（智能网页搜索）
  - 传统搜索引擎（Serper/Bing）
- **知识图谱构建**：自动提取实体、关系和洞察
- **Zep Cloud 集成** 🆕：知识图谱持久化存储、增量更新和历史读取
- **Token高效优化**：精心设计的数据传递策略
- **事实验证机制**：基于来源可靠度和交叉验证的置信度评分

## 架构设计

### Agent组成
1. **Planner**: 解析用户需求，根据5W拆解维度，支持行业信息嵌入
   - 支持用户交互：生成计划后可由用户确认或修改
2. **Researcher**: 关键词与检索式构建与扩展，执行信息检索和数据收集
   - 支持用户交互：生成检索策略后可由用户确认或修改检索词和检索式
3. **Fact Checker**: 验证事实准确性和来源可靠性（动态confidence计算）
4. **Ontology Builder**: 构建行业研究信息优化版知识图谱，分析实体关联（含详细属性和洞察）
5. **Report Writer**: 基于验证的事实和本体生成报告，包含完整事实信息

### 工作流程
```
用户查询 
  ↓
[1] Planner: 生成研究计划 
  ↓ (可选: 用户确认/修改计划)
  ↓
[2] Researcher: 生成检索策略 (关键词+检索式)
  ↓ (可选: 用户确认/修改检索策略)
  ↓
[2] Researcher: 执行检索 (微信公众号 + Twitter账号 + 网页搜索)
  ↓
[3] Fact Checker: 事实验证
  ↓
[4] Ontology Builder: 构建知识图谱
  ↓
[5] Report Writer: 生成分析报告
```

### Token优化策略
1. **增量传递**: Agent间仅传递结构化关键数据
2. **状态管理**: 集中式状态避免重复数据传递
3. **精简Prompt**: 使用简洁指令模板
4. **流式处理**: 支持流式输出减少内存占用
5. **智能缓存**: 复用中间结果

### 交互式工作流 🆕

系统支持灵活的交互式确认机制，让用户可以在关键节点介入：

#### 1. 计划确认（Plan Confirmation）
- **触发时机**: Planner Agent 生成研究计划后
- **用户选项**:
  - 确认并继续
  - 修改计划（输入修改后的 JSON）
  - 取消分析
- **启用方式**: `interactive_plan=True`（默认启用）
- **禁用方式**: `--no-plan-confirm` 或 `interactive_plan=False`

#### 2. 检索策略确认（Search Strategy Confirmation）
- **触发时机**: Researcher Agent 生成检索策略后
- **用户选项**:
  - 确认并继续检索
  - 修改检索词组
  - 修改检索式
  - 同时修改两者
  - 取消分析
- **启用方式**: `interactive_search=True`（默认启用）
- **禁用方式**: `--no-search-confirm` 或 `interactive_search=False`

#### 3. 使用场景

**交互式分析**（默认，适合探索性研究）:
```bash
./run.sh -q "分析主题"
# 可在计划和检索策略阶段进行调整
```

**半自动分析**（仅确认计划）:
```bash
./run.sh -q "分析主题" --no-search-confirm
# 确认研究计划后自动执行检索和后续步骤
```

**完全自动分析**（适合批量任务、脚本调用）:
```bash
./run.sh -q "分析主题" --no-interactive
# 全流程自动执行，无需用户介入
```

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目后，安装依赖
pip install -r requirements.txt

# 或使用虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件（从模板复制）：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必需的 API Key：

```bash
# 必需：Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_api_key

# 可选：微信公众号爬取
WECHAT_API_KEY=your_wechat_api_key

# 可选：Twitter/X 爬取
TWITTER_BEARER_TOKEN=your_twitter_bearer_token  # Twitter 官方 API
# 或使用 RapidAPI（二选一）
RAPIDAPI_KEY=your_rapidapi_key                  # RapidAPI Twitter API

# 可选：Zep Cloud 知识图谱
ZEP_API_KEY=your_zep_cloud_api_key

# 可选：模型配置
MODEL=claude-sonnet-4-6
MAX_TOKENS=4096
```

### 3. 运行方式

#### 方式一：使用 run.sh 脚本（推荐）

最简单的方式，自动处理环境变量和依赖：

```bash
# 基础分析
./run.sh -q "分析AI芯片行业发展趋势"

# 指定公众号和时间范围
./run.sh -q "新能源汽车市场分析" \
  -w "36氪,机器之心,虎嗅APP" \
  -d "2026-01-01到2026-04-15"

# 指定 Twitter 账号
./run.sh -q "AI领域最新动态" \
  -t "elonmusk,sama,ylecun" \
  -d "2026-04-01到2026-04-21"

# 混合数据源（微信 + Twitter + 网页搜索）
./run.sh -q "全球AI行业分析" \
  -w "36氪,机器之心" \
  -t "sama,ylecun" \
  -d "2026-01-01到2026-04-15"

# 使用 Session ID 进行持续跟踪
./run.sh -q "AI行业Q1分析" -s "ai_industry_2026"

# 查看帮助
./run.sh --help

# 运行交互式示例
./run.sh examples
```

#### 方式二：直接使用 CLI

```bash
# 直接调用 CLI（需要先配置环境变量）
python3 cli/cli.py -q "分析2026年AI大模型产业趋势"

# 带所有参数的完整示例
python3 cli/cli.py \
  -q "AI大模型企业应用分析" \
  -w "36氪,机器之心,虎嗅APP" \
  -d "2026-01-01到2026-04-15" \
  -s "ai_enterprise_2026"
```

#### 方式三：Python 代码调用

```python
from main import IndustryAnalyst

# 基础使用
analyst = IndustryAnalyst()
result = analyst.analyze("分析2026年AI大模型产业趋势")
print(result["report"])
```

### 4. CLI 参数说明

#### 必需参数

- `-q, --query <查询>`: 分析主题/需求（必需）

#### 可选参数

**数据源配置:**
- `-w, --wechat <账号>`: 微信公众号列表（逗号分隔）
- `-t, --twitter <账号>`: Twitter/X 账号列表（逗号分隔，不带@）
- `-d, --date <范围>`: 时间范围（格式：`YYYY-MM-DD到YYYY-MM-DD`）

**知识图谱:**
- `-s, --session <ID>`: Session ID（用于 Zep Cloud 持续跟踪）
- `--no-zep`: 禁用 Zep Cloud 知识图谱

**交互模式:** 🆕
- `--no-interactive`: 禁用所有交互式确认（完全自动执行）
- `--no-plan-confirm`: 禁用计划确认（仅自动执行计划生成）
- `--no-search-confirm`: 禁用检索确认（仅自动执行检索策略）

**输出控制:**
- `--no-verbose`: 简洁输出模式

**其他:**
- `-h, --help`: 显示帮助信息

**说明:**
- 默认启用交互式确认（计划和检索策略都需要用户确认）
- 使用 `--no-interactive` 可完全自动执行，适合批量分析或脚本调用
- 可单独控制计划或检索策略的交互行为

### 5. 使用示例

#### 示例 1：基础分析（交互式，默认） 

```bash
./run.sh -q "分析人工智能在医疗领域的应用现状"
# 会在生成计划和检索策略后等待用户确认
# 用户可以选择：1) 确认继续 2) 修改 3) 取消
```

#### 示例 2：完全自动执行（无交互） 

```bash
./run.sh -q "新能源汽车市场分析" --no-interactive
# 完全自动执行，不等待用户确认，适合脚本调用
```

#### 示例 3：仅确认计划，自动执行检索 

```bash
./run.sh -q "AI芯片行业分析" --no-search-confirm
# 生成计划后需要用户确认，但检索策略自动执行
```

#### 示例 4：指定微信公众号（交互式）

```bash
./run.sh -q "新能源汽车市场分析" -w "36氪,机器之心,虎嗅APP"
# 交互式确认，可修改计划和检索策略
```

#### 示例 5：指定时间范围（自动执行）

```bash
./run.sh -q "AI行业2026年Q1分析" -d "2026-01-01到2026-03-31" --no-interactive
# 指定时间范围，自动执行全流程
```

#### 示例 6：完整配置（自动执行）

```bash
./run.sh \
  -q "AI大模型企业应用分析" \
  -w "36氪,机器之心,虎嗅APP" \
  -d "2026-01-01到2026-04-15" \
  -s "ai_enterprise_2026" \
  --no-interactive
# 完整配置，自动执行，适合生产环境
```

#### 示例 7：持续跟踪（使用相同 Session ID）

```bash
# 第一次分析（Q1，交互式）
./run.sh -q "AI行业Q1分析" -s "ai_industry_2026" -d "2026-01-01到2026-03-31"

# 第二次分析（Q2，自动增量更新）
./run.sh -q "AI行业Q2分析" -s "ai_industry_2026" -d "2026-04-01到2026-06-30" --no-interactive
```

#### 示例 8：Twitter 账号爬取 

```bash
# 爬取指定 Twitter 账号（AI 领域意见领袖）
./run.sh -q "分析AI领域最新观点和趋势" \
  -t "elonmusk,sama,ylecun,goodfellow_ian" \
  -d "2026-04-01到2026-04-21"

# 混合数据源：微信 + Twitter
./run.sh -q "全球AI行业动态对比分析" \
  -w "机器之心,量子位,AI前线" \
  -t "sama,ylecun,AndrewYNg" \
  -d "2026-04-01到2026-04-21" \
  --no-interactive
```

### 6. Python 代码调用

#### 基础使用（交互式，默认） 

```python
from main import IndustryAnalyst

analyst = IndustryAnalyst()
result = analyst.analyze("分析2026年AI大模型产业趋势")
# 默认启用交互式确认，会在生成计划和检索策略后等待用户输入
print(result["report"])
```

#### 自动执行（禁用交互） 

```python
from main import IndustryAnalyst

analyst = IndustryAnalyst()
result = analyst.analyze(
    query="分析2026年AI大模型产业趋势",
    interactive_plan=False,      # 禁用计划确认
    interactive_search=False     # 禁用检索确认
)
# 完全自动执行，适合脚本和批量任务
print(result["report"])
```

#### 使用微信公众号爬取

```python
from main import IndustryAnalyst

analyst = IndustryAnalyst(
    wechat_api_key="your_wechat_api_key"
)

result = analyst.analyze(
    query="分析新能源汽车行业发展趋势",
    wechat_accounts=["36氪", "虎嗅APP", "钛媒体"],  # 指定公众号
    date_range="2026-01-01到2026-04-14",  # 限定时间范围
    interactive_plan=True,      # 启用计划确认
    interactive_search=False    # 禁用检索确认（自动执行检索）
)

print(result["report"])
```

#### 使用 Twitter 账号爬取 

```python
from main import IndustryAnalyst

analyst = IndustryAnalyst(
    twitter_bearer_token="your_twitter_bearer_token",  # 官方 API
    twitter_api_type="official"  # 或 "rapidapi"
)

result = analyst.analyze(
    query="分析AI领域最新观点和趋势",
    twitter_accounts=["sama", "ylecun", "goodfellow_ian"],  # 不带 @
    date_range="2026-04-01到2026-04-21",
    interactive_plan=False,
    interactive_search=False
)

print(result["report"])
```

#### 混合数据源（微信 + Twitter + 网页搜索）

```python
from main import IndustryAnalyst

analyst = IndustryAnalyst(
    wechat_api_key="your_wechat_key",
    twitter_bearer_token="your_twitter_token"
)

result = analyst.analyze(
    query="全球AI行业动态对比分析",
    wechat_accounts=["机器之心", "量子位"],      # 中文资讯
    twitter_accounts=["sama", "ylecun"],         # 英文观点
    date_range="2026-04-01到2026-04-21",
    interactive_plan=False,
    interactive_search=False
)

print(result["report"])
```

#### 使用 Zep Cloud 知识图谱

```python
from main import IndustryAnalyst

analyst = IndustryAnalyst(
    zep_api_key="your_zep_api_key",
    enable_zep=True  # 启用 Zep Cloud
)

# 首次分析（创建图谱，交互式）
result1 = analyst.analyze(
    query="AI芯片行业Q1分析",
    session_id="ai_chips_2026",  # 指定会话ID
    interactive_plan=True,
    interactive_search=True
)

# 后续分析（增量更新，自动执行）
result2 = analyst.analyze(
    query="AI芯片行业Q2分析",
    session_id="ai_chips_2026",  # 使用相同ID，自动增量更新
    interactive_plan=False,      # 自动执行
    interactive_search=False
)
# 报告中会体现历史知识和趋势变化

print(result2["report"])
```

## 微信公众号功能

### 获取 API Key

1. 访问 https://down.mptext.top
2. 登录后在「API」页面获取密钥
3. 密钥有效期：**4天**（与登录会话绑定）

### 支持的功能

- 公众号搜索（模糊匹配）
- 文章列表获取（分页支持）
- 关键词过滤（标题+摘要）
- 日期范围过滤
- 自动格式化为研究数据

### 常用公众号

**科技/创业**: 36氪、虎嗅APP、钛媒体、极客公园、品玩  
**财经/商业**: 财新周刊、第一财经、经济观察报  
**垂直领域**: 36氪汽车、机器之心、半导体行业观察

详细文档：[HOW_TO_RUN.md](HOW_TO_RUN.md)

## Twitter/X 账号爬取功能 

### 获取 API 访问权限

系统支持两种 Twitter API：

#### 方式一：Twitter 官方 API v2（推荐）

1. 访问: https://developer.twitter.com/
2. 注册开发者账号（免费）
3. 创建 App 获取 Bearer Token
4. 配置到 `.env` 文件：`TWITTER_BEARER_TOKEN=your_token`

**优点**：
- 免费使用
- 官方支持，稳定可靠
- 数据准确性高

#### 方式二：RapidAPI Twitter API（付费）

1. 访问: https://rapidapi.com/
2. 搜索 "Twitter API"
3. 订阅服务并获取 API Key
4. 配置到 `.env` 文件：`RAPIDAPI_KEY=your_key`

**优点**：
- 无需申请开发者账号
- 按需付费，使用灵活

### 支持的功能

- 用户推文获取（指定账号）
- 时间范围过滤（精确到日期）
- 关键词过滤（可选）
- 文本内容提取（不包含互动指标）
- 批量账号爬取

### 常用 Twitter 账号

**AI/机器学习领域**:
- `sama` - Sam Altman (OpenAI CEO)
- `ylecun` - Yann LeCun (Meta AI Chief)
- `AndrewYNg` - Andrew Ng (DeepLearning.AI)
- `goodfellow_ian` - Ian Goodfellow (GAN 发明者)
- `karpathy` - Andrej Karpathy (前 Tesla AI Director)

**科技/创业**:
- `elonmusk` - Elon Musk
- `satyanadella` - Satya Nadella (Microsoft CEO)
- `sundarpichai` - Sundar Pichai (Google CEO)

**使用示例**:
```bash
# 爬取 AI 领域意见领袖观点
./run.sh -q "AI行业最新观点" -t "sama,ylecun,karpathy"

# 混合数据源
./run.sh -q "全球AI动态" -w "机器之心" -t "sama,ylecun"
```

详细文档：[docs/TWITTER_INTEGRATION.md](docs/TWITTER_INTEGRATION.md)

## run.sh 脚本详解

`run.sh` 是项目的统一入口脚本，自动处理环境变量、虚拟环境和依赖检查。

### 脚本功能

1. **自动环境检查**
   - 检查并加载 `.env` 文件
   - 验证必需的 API Keys
   - 检查 Python 环境和依赖

2. **虚拟环境管理**
   - 自动检测 `venv` 或 `.venv` 目录
   - 自动激活虚拟环境（如存在）

3. **灵活的运行方式**
   - 支持直接参数传递给 CLI
   - 支持运行交互式示例
   - 支持查看帮助信息

### 使用方法

#### 直接运行 CLI（推荐）

```bash
# 最简单的方式
./run.sh -q "分析主题"

# 等同于
./run.sh cli.py -q "分析主题"
```

#### 运行示例脚本

```bash
# 运行交互式示例（展示各种使用场景）
./run.sh examples

# 等同于
bash cli/examples.sh
```

#### 查看帮助

```bash
# 显示 CLI 帮助信息
./run.sh --help

# 或
./run.sh -h
```

### 错误处理

脚本会自动检查并提示以下问题：

1. **缺少 .env 文件**
   ```
   ⚠️  未找到 .env 文件
   从 .env.example 创建 .env...
   ✓ .env 已创建，请编辑并配置 API Keys
   ```

2. **缺少 ANTHROPIC_API_KEY**
   ```
   ❌ 错误：未设置 ANTHROPIC_API_KEY
   请在 .env 文件中配置
   ```

3. **缺少依赖**
   ```
   ❌ 缺少依赖包
   请运行: pip install -r requirements.txt
   ```

### 高级用法

```bash
# 1. 使用 Python 脚本路径
./run.sh main.py

# 2. 传递复杂参数
./run.sh -q "AI行业分析" \
  -w "36氪,机器之心,虎嗅APP" \
  -d "2026-01-01到2026-04-15" \
  -s "session_001"

# 3. 禁用某些功能
./run.sh -q "分析主题" --no-zep --no-verbose
```

## 配置

### 环境变量配置

在 `.env` 文件中配置：

```bash
# === 必需配置 ===
ANTHROPIC_API_KEY=your_anthropic_key

# === 可选配置 ===

# 微信公众号爬取（如需使用公众号数据）
WECHAT_API_KEY=your_wechat_key

# Twitter/X 爬取（如需使用 Twitter 数据）
TWITTER_BEARER_TOKEN=your_twitter_bearer_token  # Twitter 官方 API（推荐）
# 或使用 RapidAPI（二选一）
RAPIDAPI_KEY=your_rapidapi_key                  # RapidAPI Twitter API

# Zep Cloud 知识图谱（如需持久化图谱）
ZEP_API_KEY=your_zep_key

# 模型配置
MODEL=claude-sonnet-4-6
MAX_TOKENS=4096

# 网页搜索（可选，默认使用 Claude Web Search）
SERPER_API_KEY=your_serper_key  # Google 搜索
# 或
BING_API_KEY=your_bing_key      # Bing 搜索
```

### API Key 获取

1. **Anthropic API Key** (必需)
   - 访问: https://console.anthropic.com/
   - 创建账号并获取 API Key

2. **微信公众号 API Key** (可选)
   - 访问: https://down.mptext.top
   - 登录后在「API」页面获取密钥
   - 有效期：4天（与登录会话绑定）

3. **Twitter API** (可选) 🆕
   - **官方 API**（推荐）：访问 https://developer.twitter.com/，注册开发者账号，创建 App 获取 Bearer Token
   - **RapidAPI**（付费）：访问 https://rapidapi.com/，搜索并订阅 Twitter API 服务

4. **Zep Cloud API Key** (可选)
   - 访问: https://www.getzep.com/
   - 创建账号并获取 API Key

## 常用命令速查

### 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env 并配置 ANTHROPIC_API_KEY

# 3. 运行示例
./run.sh examples

# 4. 执行分析（交互式，默认）
./run.sh -q "你的分析主题"
```

### 常用场景

```bash
# 基础分析（交互式，默认）
./run.sh -q "分析AI芯片行业"

# 完全自动执行（无交互）
./run.sh -q "分析AI芯片行业" --no-interactive

# 仅确认计划，自动检索 
./run.sh -q "分析AI芯片行业" --no-search-confirm

# 深度分析（含公众号，交互式）
./run.sh -q "新能源汽车分析" -w "36氪,虎嗅APP"

# 深度分析（含公众号，自动执行）
./run.sh -q "新能源汽车分析" -w "36氪,虎嗅APP" --no-interactive

# 爬取 Twitter 账号 
./run.sh -q "AI最新观点" -t "sama,ylecun" --no-interactive

# 混合数据源（微信 + Twitter）
./run.sh -q "全球AI动态" -w "机器之心" -t "sama,ylecun" --no-interactive

# 指定时间范围（自动执行）
./run.sh -q "Q1市场分析" -d "2026-01-01到2026-03-31" --no-interactive

# 持续跟踪（交互式）
./run.sh -q "Q1分析" -s "project_2026"

# 持续跟踪（自动执行）
./run.sh -q "Q2分析" -s "project_2026" --no-interactive

# 查看帮助
./run.sh --help
```

### Python 调用

```python
from main import IndustryAnalyst

# 快速分析（交互式，默认）
analyst = IndustryAnalyst()
result = analyst.analyze("你的查询")
print(result["report"])

# 自动执行（无交互）
result = analyst.analyze(
    query="你的查询",
    interactive_plan=False,
    interactive_search=False
)

# 完整配置（自动执行）
analyst = IndustryAnalyst(
    wechat_api_key="your_key",
    twitter_bearer_token="your_twitter_token", 
    zep_api_key="your_key",
    enable_zep=True
)

result = analyst.analyze(
    query="分析主题",
    wechat_accounts=["36氪", "虎嗅APP"],
    twitter_accounts=["sama", "ylecun"],  
    date_range="2026-01-01到2026-04-15",
    session_id="my_session",
    interactive_plan=False,      
    interactive_search=False
)
```

## Zep Cloud 知识图谱 

使用 [Zep Cloud](https://www.getzep.com/) 进行知识图谱的持久化存储和管理：

- **自动存储**：每次分析后自动保存知识图谱
- **增量更新**：后续分析自动合并到现有图谱
- **历史读取**：撰写报告时自动利用历史知识
- **Session 管理**：支持多个独立的分析会话

详细文档：[ZEP_CLOUD_INTEGRATION.md](ZEP_CLOUD_INTEGRATION.md)

## 项目结构

```
industry_analyst/
├── run.sh                    # 统一运行脚本（推荐入口）⭐
├── main.py                   # 主协调器
├── cli/
│   ├── cli.py               # 命令行工具
│   └── examples.sh          # 交互式示例脚本
├── agents/                   # 5个专业 Agent
│   ├── planner.py           # 研究计划生成
│   ├── researcher.py        # 信息检索与收集
│   ├── fact_checker.py      # 事实验证
│   ├── ontology_builder.py  # 知识图谱构建
│   └── report_writer.py     # 报告生成
├── utils/                    # 工具模块
│   ├── state_manager.py     # 状态管理
│   ├── wechat_crawler.py    # 微信公众号爬取
│   ├── twitter_crawler.py   # Twitter/X 爬取 
│   ├── zep_graph_manager.py # Zep Cloud 集成
│   ├── web_searcher.py      # 网页搜索
│   └── claude_web_searcher.py # Claude Web Search
├── prompts/
│   └── templates.py         # Prompt 模板
├── .env.example             # 环境变量模板
├── requirements.txt         # Python 依赖
└── README.md               # 本文档
```

## 输出文件

运行分析后，会生成以下文件：

```
findings_output/             # Research findings 详情
├── findings_YYYYMMDD_HHMMSS.json  # JSON 格式
└── findings_YYYYMMDD_HHMMSS.md    # Markdown 格式（易读）

analysis_checkpoint.json     # 分析检查点（如启用）
```

## 故障排查

### 常见问题

**1. 提示 "未设置 ANTHROPIC_API_KEY"**
```bash
# 解决方案：配置 .env 文件
cp .env.example .env
# 编辑 .env，添加：ANTHROPIC_API_KEY=your_key
```

**2. 提示 "缺少依赖包"**
```bash
# 解决方案：安装依赖
pip install -r requirements.txt
```

**3. 微信公众号爬取失败**
- 检查 `WECHAT_API_KEY` 是否配置
- 密钥有效期为4天，可能需要重新获取
- 确认公众号名称正确（支持模糊匹配）

**4. Zep Cloud 连接失败**
- 检查 `ZEP_API_KEY` 是否配置
- 确认网络连接正常
- 可以使用 `--no-zep` 参数禁用

**5. run.sh 无法执行**
```bash
# 解决方案：添加执行权限
chmod +x run.sh
```

**6. 虚拟环境问题**
```bash
# 重新创建虚拟环境
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 相关文档

- [HOW_TO_RUN.md](HOW_TO_RUN.md) - 详细运行指南
- [ZEP_CLOUD_INTEGRATION.md](ZEP_CLOUD_INTEGRATION.md) - Zep Cloud 集成文档
- [docs/TWITTER_INTEGRATION.md](docs/TWITTER_INTEGRATION.md) - Twitter 爬取功能文档 🆕
- [RUN_GUIDE.md](RUN_GUIDE.md) - 环境配置指南

## 贡献与支持

如有问题或建议，欢迎提交 Issue 或 Pull Request。

## 许可证

MIT License
