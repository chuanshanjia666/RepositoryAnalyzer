import os
import json
import git
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from html_generator import generate_git_tree_html
from analysis_visualizer import run_visualizations
import analyze
from code_analyzer import AdvancedRadonAnalyzer
from dependency_analyzer import DependencyAnalyzer
from vulnerability_scanner import AdvancedVulnerabilityScanner
from github_issue_analyzer import GitHubIssueAnalyzer
from github_actions_analyzer import GitHubActionsAnalyzer
from pr_analysis import analyze_pr_repository
BASE_DIR = Path(__file__).parent
dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"已加载配置文件: {dotenv_path}")
else:
    print(f"未找到 .env 文件: {dotenv_path}")
GIT_URL = os.getenv("GIT_URL", "https://github.com/Neutree/COMTool.git")
REPO_PATH = Path(os.getenv("REPO_PATH", str(BASE_DIR / "repo")))
REPORT_DIR = Path(os.getenv("REPORT_DIR", str(BASE_DIR / "reports")))
PREFIX = os.getenv("PREFIX", "comtool_")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Neutree/COMTool")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or None
PR_ANALYSIS_ENABLED = os.getenv("PR_ANALYSIS_ENABLED", "True").lower() == "true"
PR_ANALYSIS_REPO = os.getenv("PR_ANALYSIS_REPO", GITHUB_REPO)
PR_ANALYSIS_DAYS_THRESHOLD = int(os.getenv("PR_ANALYSIS_DAYS_THRESHOLD", "7"))
MAX_COMMITS = int(os.getenv("MAX_COMMITS", "300"))
GITHUB_ISSUE_DAYS = int(os.getenv("GITHUB_ISSUE_DAYS", "180"))

def clone_repo(url, path):
    path = Path(path)
    if not path.exists():
        print(f"克隆仓库 {url} 到 {path.absolute()}...")
        try:
            repo = git.Repo.clone_from(
                url,
                path,
                depth=100,
                timeout=300
            )
            return repo
        except git.GitCommandError as e:
            print(f"Git命令执行失败：{str(e)}")
        except TimeoutError:
            print(f"克隆仓库超时（300秒）")
        except Exception as e:
            print(f"克隆仓库失败：{str(e)}")
        return None
    else:
        print(f"仓库已存在：{path.absolute()}")
    try:
        return git.Repo(path)
    except Exception as e:
        print(f"加载本地仓库失败：{e}")
        return None

def get_git_history(repo, limit=100):
    if not repo:
        return []
    commits = []
    try:
        for idx, commit in enumerate(repo.iter_commits('--all', max_count=limit, topo_order=True)):
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
            if idx % 50 == 0 and idx > 0:
                print(f"   已读取 {idx}/{limit} 个提交记录")
    except Exception as e:
        print(f"获取提交历史失败：{str(e)}")
        return commits[::-1]
    return commits[::-1]

def setup_environment():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        test_file = REPORT_DIR / ".write_test"
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        print(f"无写入权限：{REPORT_DIR.absolute()}")
        return False
    return True
if __name__ == "__main__":
    print("启动代码分析工具...")
    print(f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本：{sys.version}")
    if not setup_environment():
        sys.exit(1)
    repo = clone_repo(GIT_URL, REPO_PATH)
    if not repo:
        print(" 仓库加载失败，程序退出")
        sys.exit(1)
    print("\n读取Git提交历史...")
    commits = get_git_history(repo, MAX_COMMITS)
    print(f"共读取 {len(commits)} 个提交记录")
    print("\n执行基础Git分析...")
    try:
        analyze.run_all_analysis(repo, commits, output_dir=str(REPORT_DIR), prefix=PREFIX)
        run_visualizations(str(REPORT_DIR), prefix=PREFIX)
        generate_git_tree_html(commits, GIT_URL)
        print("基础Git分析完成")
    except Exception as e:
        print(f"基础Git分析失败：{e}")
    print("\n" + "="*50)
    print("开始执行深度代码分析...")
    print("="*50 + "\n")
    print("分析代码复杂度...")
    try:
        radon_analyzer = AdvancedRadonAnalyzer(str(REPO_PATH), str(REPORT_DIR))
        radon_results = radon_analyzer.batch_analyze()
        if not isinstance(radon_results, (list, tuple, dict)):
            radon_results = []
            print("复杂度分析结果异常，已重置为空列表")
        radon_analyzer.visualize_complexity(radon_results)
        print(f"复杂度分析完成（有效文件数：{len(radon_results) if isinstance(radon_results, list) else 'N/A'}）")
    except Exception as e:
        print(f"复杂度分析失败：{e}")
    print("\n分析项目依赖...")
    try:
        dep_analyzer = DependencyAnalyzer(str(REPO_PATH), str(REPORT_DIR))
        python_deps = dep_analyzer.analyze_python_deps()
        dep_analyzer.analyze_generic_deps()
        dep_analyzer.visualize_deps(python_deps)
        print("依赖分析完成")
    except RuntimeError as e:
        print(f"依赖分析部分失败：{e}")
    except Exception as e:
        print(f"依赖分析失败：{e}")
    print("\n扫描代码漏洞...")
    try:
        vuln_scanner = AdvancedVulnerabilityScanner(str(REPO_PATH), str(REPORT_DIR))
        bandit_results = vuln_scanner.advanced_bandit_scan()
        vuln_scanner.visualize_vulns(bandit_results)
        print("漏洞扫描完成")
    except Exception as e:
        print(f"漏洞扫描失败：{e}")
    print("\n分析GitHub安全issues...")
    if GITHUB_REPO:
        try:
            owner, repo_name = GITHUB_REPO.split('/')
            github_analyzer = GitHubIssueAnalyzer(
                repo_owner=owner,
                repo_name=repo_name,
                output_dir=str(REPORT_DIR),
                token=GITHUB_TOKEN
            )
            print(f"   获取 {GITHUB_REPO} 的issues（最近{GITHUB_ISSUE_DAYS}天）...")
            issues = github_analyzer.get_issues(days_back=GITHUB_ISSUE_DAYS)
            if issues:
                analysis_results = github_analyzer.analyze_security_issues(issues)
                trend_data = github_analyzer.analyze_issue_trends(issues)
                github_analyzer.save_results(analysis_results, trend_data)
                github_analyzer.visualize_results(analysis_results, trend_data)
                security_count = len(analysis_results.get('security_issues', []))
                if security_count > 0:
                    print(f"   发现 {security_count} 个安全相关的issues")
                    for severity, count in analysis_results.get('severity_count', {}).items():
                        if count > 0:
                            print(f"      {severity}: {count} 个")
                else:
                    print("   未发现安全相关的issues")
            else:
                print("   未获取到GitHub issues")
        except Exception as e:
            print(f"   GitHub分析失败: {str(e)[:200]}")
    else:
        print("   未配置GitHub仓库，跳过issue分析")
    print("\n分析GitHub PR数据...")
    if PR_ANALYSIS_ENABLED and PR_ANALYSIS_REPO:
        try:
            print(f"   分析 {PR_ANALYSIS_REPO} 的PR数据...")
            pr_results = analyze_pr_repository(
                repo_full_name=PR_ANALYSIS_REPO,
                days_threshold=PR_ANALYSIS_DAYS_THRESHOLD,
                github_token=GITHUB_TOKEN
            )
            print(f"   PR分析完成，共分析 {pr_results.get('total_pr', 0)} 个PR")
        except Exception as e:
            print(f"   PR分析失败: {str(e)}")
    else:
        print("   未配置PR分析或仓库，跳过PR分析")
    print("\n分析GitHub Actions工作流...")
    if GITHUB_REPO:
        try:
            owner, repo = GITHUB_REPO.split('/')
            actions_analyzer = GitHubActionsAnalyzer(
                repo_owner=owner,
                repo_name=repo,
                output_dir=REPORT_DIR,
                token=GITHUB_TOKEN
            )
            print(f"   获取 {GITHUB_REPO} 的Actions工作流...")
            workflows = actions_analyzer.get_workflows()
            if workflows:
                security_issues = actions_analyzer.analyze_workflow_security(workflows)
                efficiency_metrics = actions_analyzer.analyze_workflow_efficiency(workflows)
                workflow_runs = actions_analyzer.get_workflow_runs(days_back=360)
                trends = actions_analyzer.analyze_workflow_trends(workflow_runs)
                actions_analyzer.save_results(security_issues, efficiency_metrics, trends)
                actions_analyzer.visualize_results(security_issues, efficiency_metrics, trends)
                if security_issues:
                    total_issues = sum(issue['total_issues'] for issue in security_issues)
                    print(f"     发现 {total_issues} 个Actions安全问题")
                    high_risk_count = sum(issue['severity_counts']['high'] for issue in security_issues)
                    if high_risk_count > 0:
                        print(f"      高风险: {high_risk_count} 个")
                else:
                    print("   未发现Actions安全问题")
                print(f"   分析了 {len(workflows)} 个工作流，{len(workflow_runs)} 次运行记录")
            else:
                print("   未获取到GitHub Actions工作流")
        except Exception as e:
            print(f"   GitHub Actions分析失败: {str(e)}")
    else:
        print("   未配置GitHub仓库，跳过Actions分析")
    print("\n所有分析完成！")
    print(f"报告目录：{REPORT_DIR.absolute()}")
    print(f"Git可视化页面：{(BASE_DIR / 'git_tree.html').absolute()}")
    try:
        security_files = [f for f in os.listdir(REPORT_DIR) if any(keyword in f.lower() for keyword in ['security', 'vulnerability', 'github'])]
        if security_files:
            print(f"\n安全分析报告:")
            for file in security_files:
                print(f"   - {file}")
    except Exception as e:
        print(f"\n列出安全报告文件失败：{e}")
