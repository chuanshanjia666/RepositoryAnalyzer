import os
import json
import git
from datetime import datetime

# ========== 统一导入所有模块 ==========
from html_generator import generate_git_tree_html
from analysis_visualizer import run_visualizations
import analyze
from code_analyzer import AdvancedRadonAnalyzer
from dependency_analyzer import DependencyAnalyzer
from vulnerability_scanner import AdvancedVulnerabilityScanner
from github_issue_analyzer import GitHubIssueAnalyzer

# ========== 全局配置（统一规范） ==========
GIT_URL = "https://github.com/Neutree/COMTool.git"
REPO_PATH = "./repo"
REPORT_DIR = "reports"
PREFIX = "comtool_"

# GitHub配置（可选）
GITHUB_REPO = "Neutree/COMTool"  # 格式: owner/repo
GITHUB_TOKEN = None  # 可选: GitHub token，用于提高API限制

def clone_repo(url, path):
    """克隆Git仓库（若不存在），增加异常处理"""
    if not os.path.exists(path):
        print(f"📥 克隆仓库 {url} 到 {path}...")
        try:
            git.Repo.clone_from(url, path)
        except Exception as e:
            print(f"❌ 克隆仓库失败：{str(e)}")
            return None
    else:
        print(f"📁 仓库已存在：{path}")
    return git.Repo(path) if os.path.exists(path) else None

def get_git_history(repo, limit=100):
    """获取Git提交历史，增加异常处理"""
    if not repo:
        return []
    commits = []
    try:
        for commit in repo.iter_commits('--all', max_count=limit, topo_order=True):
            commits.append({
                "hash": commit.hexsha[:7],
                "hashFull": commit.hexsha,
                "author": commit.author.name,
                "date": datetime.fromtimestamp(commit.authored_date).strftime('%Y-%m-%d %H:%M'),
                "message": commit.message.strip().split('\n')[0],
                "parents": [p.hexsha for p in commit.parents],
                "refs": [ref.name for ref in repo.refs if hasattr(ref, 'commit') and ref.commit == commit]
            })
    except Exception as e:
        print(f"❌ 获取提交历史失败：{str(e)}")
    return commits[::-1]

if __name__ == "__main__":
    # 1. 克隆仓库并获取提交历史
    repo = clone_repo(GIT_URL, REPO_PATH)
    if not repo:
        print("❌ 仓库克隆失败，程序退出")
        exit(1)
    commits = get_git_history(repo, 300)
    
    # 2. 确保报告目录存在
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    # 3. 原有基础分析逻辑（保留main分支核心）
    print("\n📊 执行基础Git分析...")
    analyze.run_all_analysis(repo, commits, output_dir=REPORT_DIR, prefix=PREFIX)
    run_visualizations(REPORT_DIR, prefix=PREFIX)
    generate_git_tree_html(commits, GIT_URL)

    # 4. 新增深度代码分析（保留master分支核心）
    print("\n" + "="*50)
    print("🔍 开始执行深度代码分析...")
    print("="*50 + "\n")

    # 4.1 复杂度分析（Radon）
    print("📈 分析代码复杂度...")
    radon_analyzer = AdvancedRadonAnalyzer(REPO_PATH, REPORT_DIR)
    radon_results = radon_analyzer.batch_analyze()
    radon_analyzer.visualize_complexity(radon_results)

    # 4.2 依赖分析
    print("\n📦 分析项目依赖...")
    dep_analyzer = DependencyAnalyzer(REPO_PATH, REPORT_DIR)
    python_deps = dep_analyzer.analyze_python_deps()
    dep_analyzer.analyze_generic_deps()
    dep_analyzer.visualize_deps(python_deps)

    # 4.3 漏洞扫描
    print("\n🛡️  扫描代码漏洞...")
    vuln_scanner = AdvancedVulnerabilityScanner(REPO_PATH, REPORT_DIR)
    bandit_results = vuln_scanner.advanced_bandit_scan()
    vuln_scanner.visualize_vulns(bandit_results)

    # 4.4 GitHub安全issue分析
    print("\n🐙 分析GitHub安全issues...")
    if GITHUB_REPO:
        try:
            # 解析owner和repo
            owner, repo = GITHUB_REPO.split('/')
            github_analyzer = GitHubIssueAnalyzer(
                repo_owner=owner,
                repo_name=repo,
                output_dir=REPORT_DIR,
                token=GITHUB_TOKEN
            )

            # 获取并分析issues
            print(f"   获取 {GITHUB_REPO} 的issues...")
            issues = github_analyzer.get_issues(days_back=180)  # 最近6个月

            if issues:
                analysis_results = github_analyzer.analyze_security_issues(issues)
                trend_data = github_analyzer.analyze_issue_trends(issues)
                github_analyzer.save_results(analysis_results, trend_data)
                github_analyzer.visualize_results(analysis_results, trend_data)

                # 显示安全issue摘要
                security_count = len(analysis_results['security_issues'])
                if security_count > 0:
                    print(f"   ⚠️  发现 {security_count} 个安全相关的issues")
                    for severity, count in analysis_results['severity_count'].items():
                        if count > 0:
                            print(f"      {severity}: {count} 个")
                else:
                    print("   ✅ 未发现安全相关的issues")
            else:
                print("   ⚠️  未获取到GitHub issues")

        except Exception as e:
            print(f"   ❌ GitHub分析失败: {str(e)}")
    else:
        print("   ⚠️  未配置GitHub仓库，跳过issue分析")

    # 最终提示
    print("\n🎉 所有分析完成！")
    print(f"📁 报告目录：{os.path.abspath(REPORT_DIR)}")
    print(f"🌐 Git可视化页面：{os.path.abspath('git_tree.html')}")

    # 显示生成的安全报告
    security_files = [f for f in os.listdir(REPORT_DIR) if 'security' in f or 'vulnerability' in f or 'github' in f]
    if security_files:
        print(f"\n🔒 安全分析报告:")
        for file in security_files:
            print(f"   - {file}")