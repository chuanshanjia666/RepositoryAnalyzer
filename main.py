import os
import json
import git
from datetime import datetime

# ========== 导入所有模块 ==========
from html_generator import generate_git_tree_html
from analysis_visualizer import run_visualizations
import analyze
from code_analyzer import AdvancedRadonAnalyzer
from dependency_analyzer import DependencyAnalyzer
from vulnerability_scanner import AdvancedVulnerabilityScanner

# 全局配置
GIT_URL = "https://github.com/Neutree/COMTool.git"
REPO_PATH = "./repo"
REPORT_DIR = "reports"
PREFIX = "comtool_"

def clone_repo(url, path):
    """克隆Git仓库（若不存在）"""
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
    """获取Git提交历史"""
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
    
    # 3. 原有分析逻辑
    print("\n📊 执行基础Git分析...")
    analyze.run_all_analysis(repo, commits, output_dir=REPORT_DIR, prefix=PREFIX)
    run_visualizations(REPORT_DIR, prefix=PREFIX)
    generate_git_tree_html(commits, GIT_URL)

    # 4. 深度代码分析
    print("\n" + "="*50)
    print("🔍 开始执行深度代码分析...")
    print("="*50 + "\n")

    # 4.1 复杂度分析
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

    # 最终提示
    print("\n🎉 所有分析完成！")
    print(f"📁 报告目录：{os.path.abspath(REPORT_DIR)}")
    print(f"🌐 Git可视化页面：{os.path.abspath('git_tree.html')}")