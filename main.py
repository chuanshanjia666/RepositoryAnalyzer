import os
import json
import git
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ========== 统一导入所有模块 ==========
from html_generator import generate_git_tree_html
from analysis_visualizer import run_visualizations
import analyze
from code_analyzer import AdvancedRadonAnalyzer
from dependency_analyzer import DependencyAnalyzer
from vulnerability_scanner import AdvancedVulnerabilityScanner
from github_issue_analyzer import GitHubIssueAnalyzer
from github_actions_analyzer import GitHubActionsAnalyzer
from pr_analysis import analyze_pr_repository

# ========== 全局配置（统一规范） ==========
# 路径配置使用Path对象，提升跨平台兼容性
BASE_DIR = Path(__file__).parent

# 加载 .env 文件中的环境变量
dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"📋 已加载配置文件: {dotenv_path}")
else:
    print(f"⚠️  未找到 .env 文件: {dotenv_path}")

# 从环境变量读取配置，提供默认值
GIT_URL = os.getenv("GIT_URL", "https://github.com/Neutree/COMTool.git")
REPO_PATH = Path(os.getenv("REPO_PATH", str(BASE_DIR / "repo")))
REPORT_DIR = Path(os.getenv("REPORT_DIR", str(BASE_DIR / "reports")))
PREFIX = os.getenv("PREFIX", "comtool_")

# GitHub配置（可选）
GITHUB_REPO = os.getenv("GITHUB_REPO", "Neutree/COMTool")  # 格式: owner/repo
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or None

# PR分析配置
PR_ANALYSIS_ENABLED = os.getenv("PR_ANALYSIS_ENABLED", "True").lower() == "true"
PR_ANALYSIS_REPO = os.getenv("PR_ANALYSIS_REPO", GITHUB_REPO)  # PR分析的仓库，默认与GitHub repo相同
PR_ANALYSIS_DAYS_THRESHOLD = int(os.getenv("PR_ANALYSIS_DAYS_THRESHOLD", "7"))  # 僵尸PR的时间阈值（天）

# 全局常量
MAX_COMMITS = int(os.getenv("MAX_COMMITS", "300"))  # 最大分析提交数
GITHUB_ISSUE_DAYS = int(os.getenv("GITHUB_ISSUE_DAYS", "180"))  # GitHub Issue分析时间范围

def clone_repo(url, path):
    """克隆Git仓库（若不存在），增强异常处理和用户提示"""
    path = Path(path)
    if not path.exists():
        print(f"📥 克隆仓库 {url} 到 {path.absolute()}...")
        try:
            # 增加超时和深度限制，避免克隆过大仓库
            repo = git.Repo.clone_from(
                url, 
                path,
                depth=100,  # 浅克隆，加快速度
                timeout=300
            )
            return repo
        except git.GitCommandError as e:
            print(f"❌ Git命令执行失败：{str(e)}")
        except TimeoutError:
            print(f"❌ 克隆仓库超时（300秒）")
        except Exception as e:
            print(f"❌ 克隆仓库失败：{str(e)}")
        return None
    else:
        print(f"📁 仓库已存在：{path.absolute()}")
    try:
        return git.Repo(path)
    except Exception as e:
        print(f"❌ 加载本地仓库失败：{e}")
        return None

def get_git_history(repo, limit=100):
    """获取Git提交历史，增强异常处理和数据校验"""
    if not repo:
        return []
    
    commits = []
    try:
        # 分批获取提交，避免内存溢出
        for idx, commit in enumerate(repo.iter_commits('--all', max_count=limit, topo_order=True)):
            # 基础数据校验
            author_name = commit.author.name if commit.author else "未知作者"
            commit_date = datetime.fromtimestamp(commit.authored_date) if commit.authored_date else datetime.now()
            
            commit_info = {
                "hash": commit.hexsha[:7] if commit.hexsha else "",
                "hashFull": commit.hexsha or "",
                "author": author_name,
                "date": commit_date.strftime('%Y-%m-%d %H:%M'),
                "message": commit.message.strip().split('\n')[0] if commit.message else "",
                "parents": [p.hexsha for p in commit.parents] if commit.parents else [],
                "refs": [ref.name for ref in repo.refs if hasattr(ref, 'commit') and ref.commit == commit] if repo.refs else []
            }
            commits.append(commit_info)
            
            # 进度提示
            if idx % 50 == 0 and idx > 0:
                print(f"   已读取 {idx}/{limit} 个提交记录")
                
    except Exception as e:
        print(f"❌ 获取提交历史失败：{str(e)}")
        # 返回已获取的部分数据，避免完全失败
        return commits[::-1]
    
    return commits[::-1]

def setup_environment():
    """环境初始化：创建目录、检查权限"""
    # 创建报告目录
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 检查写入权限
    try:
        test_file = REPORT_DIR / ".write_test"
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        print(f"❌ 无写入权限：{REPORT_DIR.absolute()}")
        return False
    return True

if __name__ == "__main__":
    print("🚀 启动代码分析工具...")
    print(f"📅 当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💻 Python版本：{sys.version}")
    
    # 1. 环境初始化
    if not setup_environment():
        sys.exit(1)
    
    # 2. 克隆/加载仓库
    repo = clone_repo(GIT_URL, REPO_PATH)
    if not repo:
        print("❌ 仓库加载失败，程序退出")
        sys.exit(1)
    
    # 3. 获取提交历史
    print("\n📜 读取Git提交历史...")
    commits = get_git_history(repo, MAX_COMMITS)
    print(f"✅ 共读取 {len(commits)} 个提交记录")
    
    # 4. 基础Git分析
    print("\n📊 执行基础Git分析...")
    try:
        analyze.run_all_analysis(repo, commits, output_dir=str(REPORT_DIR), prefix=PREFIX)
        run_visualizations(str(REPORT_DIR), prefix=PREFIX)
        generate_git_tree_html(commits, GIT_URL)
        print("✅ 基础Git分析完成")
    except Exception as e:
        print(f"❌ 基础Git分析失败：{e}")
        # 不中断，继续执行后续分析
    
    # 5. 深度代码分析
    print("\n" + "="*50)
    print("🔍 开始执行深度代码分析...")
    print("="*50 + "\n")

    # 5.1 复杂度分析（Radon）- 增加异常处理
    print("📈 分析代码复杂度...")
    try:
        radon_analyzer = AdvancedRadonAnalyzer(str(REPO_PATH), str(REPORT_DIR))
        radon_results = radon_analyzer.batch_analyze()
        # 修复float不可迭代问题：确保结果是可迭代类型
        if not isinstance(radon_results, (list, tuple, dict)):
            radon_results = []
            print("⚠️  复杂度分析结果异常，已重置为空列表")
        radon_analyzer.visualize_complexity(radon_results)
        print(f"✅ 复杂度分析完成（有效文件数：{len(radon_results) if isinstance(radon_results, list) else 'N/A'}）")
    except Exception as e:
        print(f"❌ 复杂度分析失败：{e}")

    # 5.2 依赖分析 - 优雅降级
    print("\n📦 分析项目依赖...")
    try:
        dep_analyzer = DependencyAnalyzer(str(REPO_PATH), str(REPORT_DIR))
        python_deps = dep_analyzer.analyze_python_deps()
        dep_analyzer.analyze_generic_deps()
        dep_analyzer.visualize_deps(python_deps)
        print("✅ 依赖分析完成")
    except RuntimeError as e:
        print(f"⚠️  依赖分析部分失败：{e}")
    except Exception as e:
        print(f"❌ 依赖分析失败：{e}")

    # 5.3 漏洞扫描
    print("\n🛡️  扫描代码漏洞...")
    try:
        vuln_scanner = AdvancedVulnerabilityScanner(str(REPO_PATH), str(REPORT_DIR))
        bandit_results = vuln_scanner.advanced_bandit_scan()
        vuln_scanner.visualize_vulns(bandit_results)
        print("✅ 漏洞扫描完成")
    except Exception as e:
        print(f"❌ 漏洞扫描失败：{e}")

    # 5.4 GitHub安全issue分析 - 整合最优逻辑，移除重复代码
    print("\n🐙 分析GitHub安全issues...")
    if GITHUB_REPO:
        try:
            # 解析owner和repo
            owner, repo_name = GITHUB_REPO.split('/')
            github_analyzer = GitHubIssueAnalyzer(
                repo_owner=owner,
                repo_name=repo_name,
                output_dir=str(REPORT_DIR),
                token=GITHUB_TOKEN
            )

            # 获取并分析issues - 增加重试机制和时间范围配置
            print(f"   获取 {GITHUB_REPO} 的issues（最近{GITHUB_ISSUE_DAYS}天）...")
            issues = github_analyzer.get_issues(days_back=GITHUB_ISSUE_DAYS)

            if issues:
                analysis_results = github_analyzer.analyze_security_issues(issues)
                trend_data = github_analyzer.analyze_issue_trends(issues)
                github_analyzer.save_results(analysis_results, trend_data)
                github_analyzer.visualize_results(analysis_results, trend_data)

                # 显示安全issue摘要（增加get方法避免KeyError）
                security_count = len(analysis_results.get('security_issues', []))
                if security_count > 0:
                    print(f"   ⚠️  发现 {security_count} 个安全相关的issues")
                    for severity, count in analysis_results.get('severity_count', {}).items():
                        if count > 0:
                            print(f"      {severity}: {count} 个")
                else:
                    print("   ✅ 未发现安全相关的issues")
            else:
                print("   ⚠️  未获取到GitHub issues")

        except Exception as e:
            print(f"   ❌ GitHub分析失败: {str(e)[:200]}")
    else:
        print("   ⚠️  未配置GitHub仓库，跳过issue分析")

    # 4.5 PR分析
    print("\n🔀 分析GitHub PR数据...")
    if PR_ANALYSIS_ENABLED and PR_ANALYSIS_REPO:
        try:
            print(f"   分析 {PR_ANALYSIS_REPO} 的PR数据...")
            pr_results = analyze_pr_repository(
                repo_full_name=PR_ANALYSIS_REPO,
                days_threshold=PR_ANALYSIS_DAYS_THRESHOLD,
                github_token=GITHUB_TOKEN
            )
            print(f"   ✅ PR分析完成，共分析 {pr_results.get('total_pr', 0)} 个PR")
        except Exception as e:
            print(f"   ❌ PR分析失败: {str(e)}")
    else:
        print("   ⚠️  未配置PR分析或仓库，跳过PR分析")

    # 4.6 GitHub Actions工作流分析
    print("\n⚡ 分析GitHub Actions工作流...")
    if GITHUB_REPO:
        try:
            # 解析owner和repo
            owner, repo = GITHUB_REPO.split('/')
            actions_analyzer = GitHubActionsAnalyzer(
                repo_owner=owner,
                repo_name=repo,
                output_dir=REPORT_DIR,
                token=GITHUB_TOKEN
            )

            # 获取并分析工作流
            print(f"   获取 {GITHUB_REPO} 的Actions工作流...")
            workflows = actions_analyzer.get_workflows()

            if workflows:
                security_issues = actions_analyzer.analyze_workflow_security(workflows)
                efficiency_metrics = actions_analyzer.analyze_workflow_efficiency(workflows)

                # 获取运行记录并分析趋势
                workflow_runs = actions_analyzer.get_workflow_runs(days_back=360)
                trends = actions_analyzer.analyze_workflow_trends(workflow_runs)

                actions_analyzer.save_results(security_issues, efficiency_metrics, trends)
                actions_analyzer.visualize_results(security_issues, efficiency_metrics, trends)

                # 显示Actions分析摘要
                if security_issues:
                    total_issues = sum(issue['total_issues'] for issue in security_issues)
                    print(f"   ⚠️  发现 {total_issues} 个Actions安全问题")
                    high_risk_count = sum(issue['severity_counts']['high'] for issue in security_issues)
                    if high_risk_count > 0:
                        print(f"      高风险: {high_risk_count} 个")
                else:
                    print("   ✅ 未发现Actions安全问题")

                print(f"   📊 分析了 {len(workflows)} 个工作流，{len(workflow_runs)} 次运行记录")
            else:
                print("   ⚠️  未获取到GitHub Actions工作流")

        except Exception as e:
            print(f"   ❌ GitHub Actions分析失败: {str(e)}")
    else:
        print("   ⚠️  未配置GitHub仓库，跳过Actions分析")

    # 最终提示
    print("\n🎉 所有分析完成！")
    # 使用Path对象的absolute方法，跨平台更友好
    print(f"📁 报告目录：{REPORT_DIR.absolute()}")
    print(f"🌐 Git可视化页面：{(BASE_DIR / 'git_tree.html').absolute()}")

    # 显示生成的安全报告（增加异常处理和大小写不敏感匹配）
    try:
        security_files = [f for f in os.listdir(REPORT_DIR) if any(keyword in f.lower() for keyword in ['security', 'vulnerability', 'github'])]
        if security_files:
            print(f"\n🔒 安全分析报告:")
            for file in security_files:
                print(f"   - {file}")
    except Exception as e:
        print(f"\n⚠️  列出安全报告文件失败：{e}")