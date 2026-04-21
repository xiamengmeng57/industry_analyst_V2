#!/bin/bash
# 快速示例脚本 - 展示各种使用场景

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Industry Analyst - 使用示例                           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 检查环境
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件"
    echo "   请从 .env.example 复制：cp .env.example .env"
    echo "   并配置 ANTHROPIC_API_KEY"
    exit 1
fi

echo "选择使用场景："
echo ""
echo "1. 快速分析（不含公众号）"
echo "2. 深度分析（含公众号 + 时间范围）"
echo "3. 持续跟踪（使用 Session ID）"
echo "4. 查看帮助"
echo "5. 自定义"
echo ""
read -p "请选择 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "示例 1: 快速分析"
        echo "命令: ./run.sh cli.py -q \"分析人工智能在医疗领域的应用现状\""
        echo ""
        read -p "按 Enter 执行..."
        ./run.sh cli.py -q "分析人工智能在医疗领域的应用现状"
        ;;

    2)
        echo ""
        echo "示例 2: 深度分析"
        echo "命令: ./run.sh cli.py \\"
        echo "  -q \"2026年新能源汽车市场分析\" \\"
        echo "  -w \"36氪,机器之心,虎嗅APP\" \\"
        echo "  -d \"2026-01-01到2026-04-15\""
        echo ""
        read -p "按 Enter 执行..."
        ./run.sh cli.py \
            -q "2026年新能源汽车市场分析" \
            -w "36氪,机器之心,虎嗅APP" \
            -d "2026-01-01到2026-04-15"
        ;;

    3)
        echo ""
        echo "示例 3: 持续跟踪"
        session_id="demo_$(date +%s)"
        echo "Session ID: $session_id"
        echo ""
        echo "第一次分析:"
        echo "命令: ./run.sh cli.py \\"
        echo "  -q \"AI芯片行业分析\" \\"
        echo "  -s \"$session_id\""
        echo ""
        read -p "按 Enter 执行第一次分析..."
        ./run.sh cli.py \
            -q "AI芯片行业分析" \
            -s "$session_id"

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "提示: 在实际使用中，可以用相同 Session ID 进行后续分析"
        echo "这样会自动合并历史知识，实现增量更新"
        echo ""
        echo "例如："
        echo "./run.sh cli.py -q \"AI芯片Q2分析\" -s \"$session_id\""
        ;;

    4)
        ./run.sh cli.py --help
        ;;

    5)
        echo ""
        echo "自定义分析"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""

        read -p "分析主题（必填）: " query
        if [ -z "$query" ]; then
            echo "❌ 分析主题不能为空"
            exit 1
        fi

        read -p "微信公众号（可选，逗号分隔）: " wechat
        read -p "时间范围（可选，格式: 2026-01-01到2026-04-15）: " date_range
        read -p "Session ID（可选）: " session

        # 构建命令
        cmd="./run.sh cli.py -q \"$query\""

        if [ ! -z "$wechat" ]; then
            cmd="$cmd -w \"$wechat\""
        fi

        if [ ! -z "$date_range" ]; then
            cmd="$cmd -d \"$date_range\""
        fi

        if [ ! -z "$session" ]; then
            cmd="$cmd -s \"$session\""
        fi

        echo ""
        echo "将执行命令:"
        echo "$cmd"
        echo ""
        read -p "按 Enter 执行..."

        eval $cmd
        ;;

    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 示例完成"
echo ""
echo "更多使用方法请查看: CLI_GUIDE.md"
