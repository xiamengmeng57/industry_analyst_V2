#!/bin/bash
# Industry Analyst - 运行脚本
# 自动处理环境变量和 Python 环境

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  未找到 .env 文件${NC}"
    if [ -f ".env.example" ]; then
        echo "   从 .env.example 创建 .env..."
        cp .env.example .env
        echo -e "${GREEN}✓ .env 已创建，请编辑并配置 API Keys${NC}"
    else
        echo -e "${RED}❌ 错误：未找到 .env.example${NC}"
        exit 1
    fi
fi

# 2. 加载环境变量
export $(grep -v '^#' .env | xargs)

# 3. 检查必需的环境变量
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}❌ 错误：未设置 ANTHROPIC_API_KEY${NC}"
    echo "   请在 .env 文件中配置"
    exit 1
fi

# 4. 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误：未找到 python3${NC}"
    exit 1
fi

# 5. 检查依赖
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  未找到虚拟环境，尝试直接运行...${NC}"
    # 检查是否安装了必需的包
    if ! python3 -c "import anthropic" 2>/dev/null; then
        echo -e "${RED}❌ 缺少依赖包${NC}"
        echo "   请运行: pip install -r requirements.txt"
        exit 1
    fi
fi

# 6. 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 7. 运行命令
if [ $# -eq 0 ]; then
    # 无参数：显示帮助
    python3 cli/cli.py --help
else
    # 有参数：运行指定的脚本/命令
    if [ -f "$1" ]; then
        # 如果第一个参数是文件（如 cli.py），运行它
        python3 "$@"
    elif [ "$1" = "cli.py" ]; then
        # 兼容 ./run.sh cli.py 格式
        shift
        python3 cli/cli.py "$@"
    elif [ "$1" = "examples" ]; then
        # 运行示例脚本
        bash cli/examples.sh
    else
        # 否则直接传递给 cli.py
        python3 cli/cli.py "$@"
    fi
fi
