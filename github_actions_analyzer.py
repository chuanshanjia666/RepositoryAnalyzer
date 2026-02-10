"""
GitHub Actions 分析模块 (使用PyGithub)
分析GitHub仓库的Actions工作流，识别潜在的安全和配置问题
"""
import os
import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import defaultdict
import re
plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
try:
    from github import Github, GithubException
except ImportError:
    print("  PyGithub未安装（执行：pip install PyGithub）")
    Github = None
    GithubException = Exception

class GitHubActionsAnalyzer:

    def __init__(self, repo_owner, repo_name, output_dir, token=None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.output_dir = output_dir
        self.token = token
        os.makedirs(output_dir, exist_ok=True)
        self.g = Github(token) if token else Github()

    def get_workflows(self):
        """获取GitHub Actions工作流"""
        print(f" 获取 {self.repo_owner}/{self.repo_name} 的Actions工作流...")
        if not self.g:
            print(" PyGithub未安装，跳过GitHub Actions分析")
            return []
        try:
            repo = self.g.get_repo(f"{self.repo_owner}/{self.repo_name}")
            print(f" 成功连接到仓库: {repo.full_name}")
            workflows = []
            try:
                repo_workflows = repo.get_workflows()
                for workflow in repo_workflows:
                    workflow_data = {
                        'id': workflow.id,
                        'name': workflow.name,
                        'path': workflow.path,
                        'state': workflow.state,
                        'html_url': workflow.html_url,
                        'created_at': workflow.created_at.isoformat() if workflow.created_at else None,
                        'updated_at': workflow.updated_at.isoformat() if workflow.updated_at else None,
                        'badge_url': workflow.badge_url
                    }
                    workflows.append(workflow_data)
                print(f" 获取到 {len(workflows)} 个工作流")
            except GithubException as e:
                print(f"  获取工作流失败: {str(e)}")
                workflows = self._get_workflows_from_contents(repo)
            return workflows
        except GithubException as e:
            print(f" 获取工作流失败: {str(e)}")
            return []
        except Exception as e:
            print(f" 未知错误: {str(e)}")
            return []

    def _get_workflows_from_contents(self, repo):
        """通过contents API获取workflow文件"""
        workflows = []
        try:
            workflows_dir = repo.get_contents(".github/workflows")
            if isinstance(workflows_dir, list):
                for file in workflows_dir:
                    if file.name.endswith('.yml') or file.name.endswith('.yaml'):
                        workflow_data = {
                            'id': file.sha,
                            'name': file.name,
                            'path': file.path,
                            'state': 'active',
                            'html_url': file.html_url,
                            'created_at': file.last_modified.isoformat() if file.last_modified else None,
                            'updated_at': file.last_modified.isoformat() if file.last_modified else None,
                            'content': file.decoded_content.decode('utf-8') if file.decoded_content else ''
                        }
                        workflows.append(workflow_data)
            print(f" 通过contents API获取到 {len(workflows)} 个工作流文件")
        except GithubException as e:
            print(f"  通过contents API获取工作流失败: {str(e)}")
        return workflows

    def analyze_workflow_security(self, workflows):
        """分析工作流安全性"""
        print(" 分析Actions工作流安全性...")
        security_issues = []
        risk_patterns = {
            'high': [
                {
                    'pattern': r'uses:\s*actions/(checkout|setup-node|setup-python)@v[0-9.]+',
                    'description': '使用固定版本而非commit SHA，可能存在供应链攻击风险',
                    'suggestion': '建议使用完整的commit SHA而非版本标签'
                },
                {
                    'pattern': r'run:.*curl.*\|\s*(bash|sh|powershell)',
                    'description': '管道下载并直接执行脚本，极高风险',
                    'suggestion': '避免直接执行远程脚本，先下载检查后再执行'
                },
                {
                    'pattern': r'env:.*=.*\$\{{.*secrets.*}}',
                    'description': '敏感环境变量可能泄露',
                    'suggestion': '确保敏感信息使用secrets管理，避免日志输出'
                }
            ],
            'medium': [
                {
                    'pattern': r'uses:\s*.*@v[0-9]+(?!\.[0-9]+\.[0-9]+)',
                    'description': '使用大版本号而非精确版本',
                    'suggestion': '建议使用精确版本号(v1.2.3)而非大版本(v1)'
                },
                {
                    'pattern': r'run:.*sudo.*',
                    'description': '使用sudo可能带来权限风险',
                    'suggestion': '避免不必要的sudo使用，限制权限范围'
                },
                {
                    'pattern': r'permissions:.*',
                    'description': '权限配置可能过于宽松',
                    'suggestion': '检查权限配置，遵循最小权限原则'
                }
            ],
            'low': [
                {
                    'pattern': r'name:.*[^\w\s-]',
                    'description': '工作流名称包含特殊字符',
                    'suggestion': '使用简洁明了的名称'
                },
                {
                    'pattern': r'on:.*schedule.*',
                    'description': '定时任务配置',
                    'suggestion': '检查定时任务的安全性'
                }
            ]
        }
        for workflow in workflows:
            workflow_issues = []
            content = workflow.get('content', '')
            if not content:
                continue
            for risk_level, patterns in risk_patterns.items():
                for pattern_info in patterns:
                    pattern = pattern_info['pattern']
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        workflow_issues.append({
                            'severity': risk_level,
                            'description': pattern_info['description'],
                            'suggestion': pattern_info['suggestion'],
                            'line_content': match.group(0).strip(),
                            'line_number': content[:match.start()].count('\n') + 1
                        })
            if workflow_issues:
                security_issues.append({
                    'workflow_name': workflow.get('name', 'Unknown'),
                    'workflow_path': workflow.get('path', ''),
                    'workflow_url': workflow.get('html_url', ''),
                    'issues': workflow_issues,
                    'total_issues': len(workflow_issues),
                    'severity_counts': self._count_severities(workflow_issues)
                })
        print(f" 发现 {len(security_issues)} 个有安全问题的工作流")
        return security_issues

    def _count_severities(self, issues):
        """统计问题严重性"""
        counts = {'high': 0, 'medium': 0, 'low': 0}
        for issue in issues:
            severity = issue.get('severity', 'low')
            if severity in counts:
                counts[severity] += 1
        return counts

    def analyze_workflow_efficiency(self, workflows):
        """分析工作流效率"""
        print(" 分析Actions工作流效率...")
        efficiency_metrics = []
        for workflow in workflows:
            content = workflow.get('content', '')
            if not content:
                continue
            metrics = {
                'workflow_name': workflow.get('name', 'Unknown'),
                'job_count': len(re.findall(r'jobs:', content)),
                'step_count': len(re.findall(r'- name:', content)),
                'uses_count': len(re.findall(r'uses:', content)),
                'run_count': len(re.findall(r'run:', content)),
                'has_cache': bool(re.search(r'cache:', content)),
                'has_artifacts': bool(re.search(r'upload-artifact|download-artifact', content)),
                'has_matrix': bool(re.search(r'strategy:\s*matrix:', content)),
                'file_size': len(content)
            }
            efficiency_metrics.append(metrics)
        return efficiency_metrics

    def get_workflow_runs(self, days_back=30):
        """获取工作流运行记录"""
        print(f" 获取最近{days_back}天的工作流运行记录...")
        if not self.g:
            return []
        try:
            repo = self.g.get_repo(f"{self.repo_owner}/{self.repo_name}")
            from datetime import timezone
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            workflow_runs = []
            try:
                runs = repo.get_workflow_runs()
                for run in runs:
                    if run.created_at < cutoff_date:
                        break
                    run_data = {
                        'id': run.id,
                        'name': run.name,
                        'status': run.status,
                        'conclusion': run.conclusion,
                        'created_at': run.created_at.isoformat(),
                        'updated_at': run.updated_at.isoformat(),
                        'html_url': run.html_url,
                        'event': run.event,
                        'head_branch': run.head_branch,
                        'run_number': run.run_number,
                        'duration': (run.updated_at - run.created_at).total_seconds() if run.updated_at and run.created_at else 0
                    }
                    workflow_runs.append(run_data)
                print(f" 获取到 {len(workflow_runs)} 个工作流运行记录")
            except GithubException as e:
                print(f"  获取工作流运行失败: {str(e)}")
            return workflow_runs
        except Exception as e:
            print(f" 获取工作流运行失败: {str(e)}")
            return []

    def analyze_workflow_trends(self, workflow_runs):
        """分析工作流运行趋势"""
        print(" 分析工作流运行趋势...")
        trends = {
            'total_runs': len(workflow_runs),
            'success_rate': 0,
            'failure_rate': 0,
            'avg_duration': 0,
            'by_event': defaultdict(int),
            'by_branch': defaultdict(int),
            'by_status': defaultdict(int),
            'daily_stats': defaultdict(lambda: {'total': 0, 'success': 0, 'failure': 0})
        }
        if not workflow_runs:
            return trends
        total_duration = 0
        success_count = 0
        failure_count = 0
        for run in workflow_runs:
            if run.get('conclusion') == 'success':
                success_count += 1
            elif run.get('conclusion') == 'failure':
                failure_count += 1
            event = run.get('event', 'unknown')
            trends['by_event'][event] += 1
            branch = run.get('head_branch', 'unknown')
            trends['by_branch'][branch] += 1
            status = run.get('status', 'unknown')
            trends['by_status'][status] += 1
            created_date = run.get('created_at', '').split('T')[0]
            trends['daily_stats'][created_date]['total'] += 1
            if run.get('conclusion') == 'success':
                trends['daily_stats'][created_date]['success'] += 1
            elif run.get('conclusion') == 'failure':
                trends['daily_stats'][created_date]['failure'] += 1
            duration = run.get('duration', 0)
            if duration > 0:
                total_duration += duration
        trends['success_rate'] = (success_count / len(workflow_runs)) * 100 if workflow_runs else 0
        trends['failure_rate'] = (failure_count / len(workflow_runs)) * 100 if workflow_runs else 0
        trends['avg_duration'] = total_duration / len(workflow_runs) if workflow_runs else 0
        return trends

    def save_results(self, security_issues, efficiency_metrics, trends):
        """保存分析结果"""
        security_output_path = os.path.join(self.output_dir, "github_actions_security.json")
        with open(security_output_path, 'w', encoding='utf-8') as f:
            json.dump(security_issues, f, ensure_ascii=False, indent=4)
        efficiency_output_path = os.path.join(self.output_dir, "github_actions_efficiency.json")
        with open(efficiency_output_path, 'w', encoding='utf-8') as f:
            json.dump(efficiency_metrics, f, ensure_ascii=False, indent=4)
        trends_output_path = os.path.join(self.output_dir, "github_actions_trends.json")
        with open(trends_output_path, 'w', encoding='utf-8') as f:
            trends_data = dict(trends)
            trends_data['by_event'] = dict(trends['by_event'])
            trends_data['by_branch'] = dict(trends['by_branch'])
            trends_data['by_status'] = dict(trends['by_status'])
            trends_data['daily_stats'] = dict(trends['daily_stats'])
            json.dump(trends_data, f, ensure_ascii=False, indent=4)
        print(f" Actions分析结果已保存:")
        print(f"   安全问题: {security_output_path}")
        print(f"   效率指标: {efficiency_output_path}")
        print(f"   运行趋势: {trends_output_path}")

    def visualize_results(self, security_issues, efficiency_metrics, trends):
        """可视化分析结果"""
        print(" 生成Actions分析可视化图表...")
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        if security_issues:
            total_high = sum(issue['severity_counts']['high'] for issue in security_issues)
            total_medium = sum(issue['severity_counts']['medium'] for issue in security_issues)
            total_low = sum(issue['severity_counts']['low'] for issue in security_issues)
            severity_labels = ['高风险', '中风险', '低风险']
            severity_values = [total_high, total_medium, total_low]
            severity_colors = ['#ff4444', '#ffaa00', '#ffff44']
            if sum(severity_values) > 0:
                ax1.pie(severity_values, labels=severity_labels, colors=severity_colors, autopct='%1.1f%%')
            else:
                ax1.text(0.5, 0.5, '无安全问题', ha='center', va='center', fontsize=12)
        else:
            ax1.text(0.5, 0.5, '无安全问题', ha='center', va='center', fontsize=12)
        ax1.set_title('GitHub Actions安全问题分布', fontsize=14)
        if trends['total_runs'] > 0:
            success_rate = trends['success_rate']
            failure_rate = trends['failure_rate']
            other_rate = 100 - success_rate - failure_rate
            ax2.bar(['成功', '失败', '其他'], [success_rate, failure_rate, other_rate],
                   color=['#44ff44', '#ff4444', '#aaaaaa'])
            ax2.set_title(f'工作流运行成功率 ({trends["total_runs"]}次运行)', fontsize=14)
            ax2.set_ylabel('百分比 (%)', fontsize=12)
        else:
            ax2.text(0.5, 0.5, '无运行数据', ha='center', va='center', fontsize=12)
            ax2.set_title('工作流运行成功率', fontsize=14)
        if trends['by_event']:
            events = list(trends['by_event'].keys())[:5]
            event_counts = [trends['by_event'][event] for event in events]
            ax3.bar(events, event_counts, color=['#66b3ff', '#99ff99', '#ffcc99', '#ff9999', '#ff99ff'])
            ax3.set_title('工作流触发事件分布', fontsize=14)
            ax3.set_ylabel('触发次数', fontsize=12)
            plt.setp(ax3.get_xticklabels(), rotation=45)
        else:
            ax3.text(0.5, 0.5, '无事件数据', ha='center', va='center', fontsize=12)
            ax3.set_title('工作流触发事件分布', fontsize=14)
        if efficiency_metrics:
            workflow_names = [m['workflow_name'][:15] + '...' if len(m['workflow_name']) > 15 else m['workflow_name']
                            for m in efficiency_metrics[:5]]
            step_counts = [m['step_count'] for m in efficiency_metrics[:5]]
            ax4.plot(workflow_names, step_counts, marker='o', color='#ff6666', linewidth=2)
            ax4.set_title('工作流步骤数量对比', fontsize=14)
            ax4.set_ylabel('步骤数', fontsize=12)
            plt.setp(ax4.get_xticklabels(), rotation=45)
        else:
            ax4.text(0.5, 0.5, '无效率数据', ha='center', va='center', fontsize=12)
            ax4.set_title('工作流步骤数量对比', fontsize=14)
        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, "github_actions_analysis.png")
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f" Actions分析图表已保存: {chart_path}")

def main():
    """演示使用"""
    print(" GitHub Actions 分析工具")
    print("=" * 50)
    analyzer = GitHubActionsAnalyzer(
        repo_owner="Neutree",
        repo_name="COMTool",
        output_dir="github_analysis",
        token=None
    )
    try:
        workflows = analyzer.get_workflows()
        if not workflows:
            print("  没有找到工作流")
            return
        security_issues = analyzer.analyze_workflow_security(workflows)
        efficiency_metrics = analyzer.analyze_workflow_efficiency(workflows)
        workflow_runs = analyzer.get_workflow_runs(days_back=60)
        trends = analyzer.analyze_workflow_trends(workflow_runs)
        analyzer.save_results(security_issues, efficiency_metrics, trends)
        analyzer.visualize_results(security_issues, efficiency_metrics, trends)
        print("\n Actions分析完成!")
        if security_issues:
            total_issues = sum(issue['total_issues'] for issue in security_issues)
            print(f"  发现 {total_issues} 个安全问题")
            for issue in security_issues:
                if issue['severity_counts']['high'] > 0:
                    print(f"   高风险: {issue['severity_counts']['high']} 个")
        else:
            print(" 未发现安全问题")
    except Exception as e:
        print(f" 分析失败: {str(e)}")
if __name__ == "__main__":
    main()
