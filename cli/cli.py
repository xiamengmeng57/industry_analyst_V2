#!/usr/bin/env python3
"""
Industry Analyst - 命令行工具

命令行接口，用于执行行业分析任务。

使用方法:
    ./run.sh -q "分析主题"
    python3 cli/cli.py -q "分析主题"

功能:
    - 支持微信公众号数据爬取
    - 支持时间范围过滤
    - 支持 Zep Cloud 知识图谱持久化
    - 支持 Session ID 持续跟踪
    - 详细的输出统计和进度显示

示例:
    # 基础分析
    ./run.sh -q "AI芯片行业分析"

    # 完整配置
    ./run.sh -q "新能源汽车市场" -w "36氪,虎嗅APP" -d "2026-01-01到2026-03-31" -s "ev_2026"

更多信息:
    README.md - 项目总览
    HOW_TO_RUN.md - 详细使用指南
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def show_usage():
    """显示使用说明"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║         Industry Analyst - 智能行业分析系统                    ║
╚══════════════════════════════════════════════════════════════╝

使用方法:
  ./run.sh [选项]                    # 推荐方式
  python3 cli/cli.py [选项]          # 直接调用

选项:
  -q, --query <查询>       必需：分析主题/需求
  -w, --wechat <账号>      可选：微信公众号（逗号分隔）
  -d, --date <范围>        可选：时间范围 YYYY-MM-DD到YYYY-MM-DD
  -s, --session <ID>       可选：Session ID（用于Zep Cloud持续跟踪）
  --no-zep                 可选：禁用 Zep Cloud
  --no-verbose             可选：简洁输出模式
  --no-interactive         可选：禁用交互式确认（自动执行）
  --no-plan-confirm        可选：禁用计划确认（仅禁用计划确认）
  --no-search-confirm      可选：禁用检索确认（仅禁用检索确认）
  -h, --help               显示此帮助信息

示例:

1. 基础分析（默认交互式）
   ./run.sh -q "分析AI芯片行业发展趋势"
   # 会在生成计划和检索策略后等待用户确认

2. 完全自动执行（无交互）
   ./run.sh -q "新能源汽车市场分析" --no-interactive

3. 仅确认计划，自动执行检索
   ./run.sh -q "AI行业分析" --no-search-confirm

4. 指定公众号（交互式）
   ./run.sh -q "新能源汽车市场分析" -w "36氪,机器之心,量子位"

5. 指定时间范围
   ./run.sh -q "AI行业2026年Q1分析" -d "2026-01-01到2026-03-31"

6. 完整配置（自动执行）
   ./run.sh \
     -q "AI大模型企业应用分析" \
     -w "36氪,机器之心,虎嗅APP" \
     -d "2026-01-01到2026-04-15" \
     -s "ai_enterprise_2026" \
     --no-interactive

7. 持续跟踪（使用相同 Session ID）
   # 第一次分析（Q1）
   ./run.sh -q "AI行业Q1分析" -s "ai_industry_2026" -d "2026-01-01到2026-03-31"

   # 第二次分析（Q2，自动增量更新）
   ./run.sh -q "AI行业Q2分析" -s "ai_industry_2026" -d "2026-04-01到2026-06-30"

8. 运行交互式示例
   ./run.sh examples

常用公众号:
  科技类: 36氪, 虎嗅APP, 钛媒体, 极客公园, 品玩
  AI/ML:  机器之心, 量子位, AI前线, 新智元
  财经类: 财新周刊, 第一财经, 经济观察报
  行业类: 36氪汽车, 半导体行业观察, 芯东西, 电动星球News

环境变量:
  ANTHROPIC_API_KEY  必需：Claude API Key
  WECHAT_API_KEY     可选：微信公众号 API Key
  ZEP_API_KEY        可选：Zep Cloud API Key

配置文件:
  .env               - 环境变量配置（从 .env.example 复制）

相关命令:
  ./run.sh examples  - 运行交互式示例
  ./run.sh --help    - 显示此帮助

更多信息:
  README.md          - 项目总览和快速开始
  HOW_TO_RUN.md      - 详细使用指南
  ZEP_CLOUD_INTEGRATION.md - Zep Cloud 集成文档
""")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Industry Analyst - 智能行业分析系统',
        add_help=False
    )

    parser.add_argument('-q', '--query', type=str, help='分析主题/需求')
    parser.add_argument('-w', '--wechat', type=str, help='微信公众号（逗号分隔）')
    parser.add_argument('-t', '--twitter', type=str, help='twitter账号')
    parser.add_argument('-d', '--date', type=str, help='时间范围 YYYY-MM-DD到YYYY-MM-DD')
    parser.add_argument('-s', '--session', type=str, help='Session ID')
    parser.add_argument('--no-zep', action='store_true', help='禁用 Zep Cloud')
    parser.add_argument('--no-verbose', action='store_true', help='简洁输出')
    parser.add_argument('--no-interactive', action='store_true', help='禁用所有交互式确认')
    parser.add_argument('--no-plan-confirm', action='store_true', help='禁用计划确认')
    parser.add_argument('--no-search-confirm', action='store_true', help='禁用检索确认')
    parser.add_argument('-h', '--help', action='store_true', help='显示帮助')

    args = parser.parse_args()

    # 显示帮助
    if args.help or not args.query:
        show_usage()
        return 0 if args.help else 1

    # 检查环境变量
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误：未设置 ANTHROPIC_API_KEY")
        print("   请在 .env 文件中配置或运行: export ANTHROPIC_API_KEY='your_key'")
        return 1

    # 解析参数
    query = args.query
    wechat_accounts = None
    twitter_accounts = None
    if args.wechat:
        wechat_accounts = [acc.strip() for acc in args.wechat.split(',')]
    if args.twitter:
        twitter_accounts = [acc.strip() for acc in args.twitter.split(',')]
    date_range = args.date
    session_id = args.session
    enable_zep = not args.no_zep
    verbose = not args.no_verbose

    # 交互式参数
    interactive_plan = not (args.no_interactive or args.no_plan_confirm)
    interactive_search = not (args.no_interactive or args.no_search_confirm)

    # 显示配置
    print("=" * 70)
    print("  Industry Analyst - 行业分析")
    print("=" * 70)
    print(f"\n查询主题: {query}")
    if wechat_accounts:
        print(f"公众号: {', '.join(wechat_accounts)}")
    if date_range:
        print(f"时间范围: {date_range}")
    if session_id:
        print(f"Session ID: {session_id}")
    if enable_zep:
        if os.getenv("ZEP_API_KEY"):
            print("Zep Cloud: 启用")
        else:
            print("Zep Cloud: 未配置（设置 ZEP_API_KEY 启用）")
            enable_zep = False
    else:
        print("Zep Cloud: 禁用")

    # 显示交互模式
    if interactive_plan and interactive_search:
        print("交互模式: 完全启用（计划确认 + 检索确认）")
    elif interactive_plan:
        print("交互模式: 部分启用（仅计划确认）")
    elif interactive_search:
        print("交互模式: 部分启用（仅检索确认）")
    else:
        print("交互模式: 禁用（自动执行）")

    print("\n" + "=" * 70)
    print("开始分析...")
    print("=" * 70 + "\n")

    # 执行分析
    try:
        # 添加项目根目录到 Python 路径
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))

        from main import IndustryAnalyst

        analyst = IndustryAnalyst(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            wechat_api_key=os.getenv("WECHAT_API_KEY"),
            zep_api_key=os.getenv("ZEP_API_KEY"),
            enable_zep=enable_zep,
            verbose=verbose
        )

        result = analyst.analyze(
            query=query,
            wechat_accounts=wechat_accounts,
            twitter_accounts=twitter_accounts,
            date_range=date_range,
            session_id=session_id,
            interactive_plan=interactive_plan,
            interactive_search=interactive_search
        )

        # 输出结果
        print("\n" + "=" * 70)
        print("📄 分析报告")
        print("=" * 70)
        print(result["report"])

        # 输出统计
        print("\n" + "=" * 70)
        print("📊 分析统计")
        print("=" * 70)

        plan = result.get("plan", {})
        research = result.get("research", {})
        ontology = result.get("ontology", {})

        print(f"\n研究计划:")
        print(f"  - 时间: {plan.get('time_range', '当前')}")
        print(f"  - 地区: {plan.get('region', '中国')}")
        print(f"  - 主体: {len(plan.get('subjects', []))} 个")
        print(f"  - 问题: {len(plan.get('research_questions', []))} 个")
        print(f"  - 行业: {', '.join(plan.get('industry_areas', []))}")

        print(f"\n研究结果:")
        print(f"  - 发现: {len(research.get('findings', []))} 条")

        # 显示数据源统计
        search_stats = research.get('search_stats', {})
        if search_stats:
            print(f"  - 数据来源:")
            if search_stats.get('wechat', 0) > 0:
                print(f"    • 微信公众号: {search_stats['wechat']} 条")
            if search_stats.get('claude_web', 0) > 0:
                print(f"    • Claude Web Search: {search_stats['claude_web']} 条")
            if search_stats.get('traditional_web', 0) > 0:
                print(f"    • 传统网页搜索: {search_stats['traditional_web']} 条")

        print(f"  - 检索词: {len(research.get('search_terms', []))} 组")
        print(f"  - 验证事实: {len(result.get('verified_facts', []))} 条")

        print(f"\n知识图谱:")
        print(f"  - 实体: {len(ontology.get('entities', []))} 个")
        print(f"  - 关系: {len(ontology.get('relations', []))} 个")
        print(f"  - 洞察: {len(ontology.get('insights', []))} 个")

        if session_id:
            print(f"\nSession ID: {session_id}")
            print("  提示: 使用相同 Session ID 可实现增量分析")

        # 提示输出文件位置
        print(f"\n💾 输出文件:")
        print(f"  - Findings: findings_output/findings_*.md")
        if session_id and enable_zep:
            print(f"  - 知识图谱已保存到 Zep Cloud (Session: {session_id})")

        print("\n✅ 分析完成！")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  分析已中断")
        return 130
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
