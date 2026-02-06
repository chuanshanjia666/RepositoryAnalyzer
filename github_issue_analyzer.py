#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Issue 分析模块 (使用PyGithub)
分析GitHub仓库的issue，识别安全相关的issue
"""

import os
import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import defaultdict

plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


try:
    from github import Github, GithubException
except ImportError:
    print("⚠️  PyGithub未安装（执行：pip install PyGithub）")
    Github = None
    GithubException = Exception


class GitHubIssueAnalyzer:
    def __init__(self, repo_owner, repo_name, output_dir, token=None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.output_dir = output_dir
        self.token = token

        os.makedirs(output_dir, exist_ok=True)
        self.g = Github(token) if token else Github()
        # # 初始化GitHub客户端
        # if Github:
        #     # 禁用SSL验证（仅用于测试环境）
        #     import ssl
        #     ssl._create_default_https_context = ssl._create_unverified_context
        #     self.g = Github(token) if token else Github()
        # else:
        #     self.g = None

    def get_issues(self, state='all', days_back=365):
        """获取GitHub issues"""
        print(f"🔍 获取 {self.repo_owner}/{self.repo_name} 的issues...")

        if not self.g:
            print("❌ PyGithub未安装，跳过GitHub分析")
            return []

        try:
            # 获取仓库
            repo = self.g.get_repo(f"{self.repo_owner}/{self.repo_name}")
            print(f"✅ 成功连接到仓库: {repo.full_name}")

            # 计算截止日期（使用UTC时区）
            from datetime import timezone
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

            # 获取issues
            issues = []

            # 获取开放状态的issues
            if state in ['all', 'open']:
                try:
                    open_issues = repo.get_issues(state='open')
                    for issue in open_issues:
                        if issue.created_at >= cutoff_date:
                            issues.append(self._convert_github_issue(issue))
                except GithubException as e:
                    print(f"⚠️  获取开放issues失败: {str(e)}")

            # 获取关闭状态的issues
            if state in ['all', 'closed']:
                try:
                    closed_issues = repo.get_issues(state='closed')
                    for issue in closed_issues:
                        if issue.created_at >= cutoff_date:
                            issues.append(self._convert_github_issue(issue))
                except GithubException as e:
                    print(f"⚠️  获取关闭issues失败: {str(e)}")

            print(f"✅ 获取到 {len(issues)} 个issues")
            return issues

        except GithubException as e:
            print(f"❌ 获取issues失败: {str(e)}")
            return []
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            return []

    def _convert_github_issue(self, github_issue):
        """将PyGithub Issue对象转换为字典"""
        return {
            'id': github_issue.id,
            'number': github_issue.number,
            'title': github_issue.title,
            'body': github_issue.body or '',
            'state': github_issue.state,
            'created_at': github_issue.created_at.isoformat(),
            'updated_at': github_issue.updated_at.isoformat(),
            'closed_at': github_issue.closed_at.isoformat() if github_issue.closed_at else None,
            'html_url': github_issue.html_url,
            'labels': [label.name for label in github_issue.labels],
            'assignees': [assignee.login for assignee in github_issue.assignees],
            'comments': github_issue.comments,
            'user': github_issue.user.login,
            'is_pull_request': github_issue.pull_request is not None
        }

    def analyze_security_issues(self, issues):
        """分析安全相关的issues"""
        print("🔍 分析安全相关的issues...")

        security_keywords = [
            'security', 'vulnerability', 'exploit', 'cve', 'xss', 'injection',
            'authentication', 'authorization', 'password', 'crypto', 'ssl',
            'csrf', 'xxe', 'ssrf', 'rce', 'remote code execution',
            'buffer overflow', 'sql injection', 'command injection',
            '敏感信息', '安全漏洞', '注入', '权限绕过', '越权',
            '认证绕过', '密码泄露', '加密', '密钥泄露'
        ]

        security_issues = []
        severity_count = {'high': 0, 'medium': 0, 'low': 0, 'unknown': 0}

        for issue in issues:
            # 跳过Pull Request
            if issue.get('is_pull_request'):
                continue

            title = issue.get('title', '').lower()
            body = issue.get('body', '').lower()
            labels = [label.lower() for label in issue.get('labels', [])]

            # 检查是否包含安全关键词
            is_security_issue = False
            detected_keywords = []

            for keyword in security_keywords:
                if (keyword.lower() in title or
                    keyword.lower() in body or
                    keyword.lower() in labels):
                    is_security_issue = True
                    detected_keywords.append(keyword)

            if is_security_issue:
                # 评估严重性
                severity = self._assess_severity(issue, detected_keywords)
                severity_count[severity] += 1

                security_issues.append({
                    'id': issue['id'],
                    'number': issue['number'],
                    'title': issue['title'],
                    'state': issue['state'],
                    'created_at': issue['created_at'],
                    'updated_at': issue['updated_at'],
                    'url': issue['html_url'],
                    'labels': issue['labels'],
                    'severity': severity,
                    'detected_keywords': detected_keywords,
                    'assignees': issue['assignees'],
                    'comments_count': issue['comments'],
                    'body_preview': issue['body'][:200] + '...' if len(issue['body']) > 200 else issue['body'],
                    'author': issue['user']
                })

        print(f"✅ 发现 {len(security_issues)} 个安全相关的issues")
        print(f"   高风险: {severity_count['high']} | 中风险: {severity_count['medium']} | 低风险: {severity_count['low']}")

        return {
            'security_issues': security_issues,
            'severity_count': severity_count,
            'total_issues': len([i for i in issues if not i.get('is_pull_request')]),
            'security_ratio': len(security_issues) / len([i for i in issues if not i.get('is_pull_request')]) if issues else 0
        }

    def _assess_severity(self, issue, keywords):
        """评估issue的严重性"""
        title = issue.get('title', '').lower()
        body = issue.get('body', '').lower()
        labels = [label.lower() for label in issue.get('labels', [])]

        # 高风险关键词
        high_risk_keywords = ['rce', 'remote code execution', 'sql injection',
                             'command injection', 'buffer overflow', '权限提升', '提权']

        # 中风险关键词
        medium_risk_keywords = ['xss', 'csrf', 'xxe', 'ssrf', 'injection',
                               '认证绕过', '越权', '敏感信息']

        # 检查标签
        if 'security' in labels or 'vulnerability' in labels:
            if any(keyword in labels for keyword in ['critical', 'high', '严重']):
                return 'high'
            elif any(keyword in labels for keyword in ['medium', '中']):
                return 'medium'

        # 检查关键词
        if any(keyword in title or keyword in body for keyword in high_risk_keywords):
            return 'high'
        elif any(keyword in title or keyword in body for keyword in medium_risk_keywords):
            return 'medium'
        elif any(keyword in title or keyword in body for keyword in ['security', '安全']):
            return 'low'

        return 'unknown'

    def analyze_issue_trends(self, issues):
        """分析issue趋势"""
        print("📊 分析issue趋势...")

        # 按月份统计
        monthly_stats = defaultdict(lambda: {'opened': 0, 'closed': 0, 'security': 0})

        for issue in issues:
            if issue.get('is_pull_request'):
                continue

            created_at = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
            month_key = created_at.strftime('%Y-%m')

            monthly_stats[month_key]['opened'] += 1

            if issue['state'] == 'closed' and issue.get('closed_at'):
                closed_at = datetime.fromisoformat(issue['closed_at'].replace('Z', '+00:00'))
                closed_month = closed_at.strftime('%Y-%m')
                monthly_stats[closed_month]['closed'] += 1

        # 转换为列表格式
        trend_data = []
        for month, stats in sorted(monthly_stats.items()):
            trend_data.append({
                'month': month,
                'opened': stats['opened'],
                'closed': stats['closed'],
                'pending': stats['opened'] - stats['closed']
            })

        return trend_data

    def save_results(self, analysis_results, trend_data):
        """保存分析结果"""
        # 保存安全issue分析结果
        security_output_path = os.path.join(self.output_dir, "github_security_issues_v2.json")
        with open(security_output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=4)

        # 保存趋势数据
        trend_output_path = os.path.join(self.output_dir, "github_issue_trends_v2.json")
        with open(trend_output_path, 'w', encoding='utf-8') as f:
            json.dump(trend_data, f, ensure_ascii=False, indent=4)

        print(f"✅ 分析结果已保存:")
        print(f"   安全issues: {security_output_path}")
        print(f"   Issue趋势: {trend_output_path}")

    def visualize_results(self, analysis_results, trend_data):
        """可视化分析结果"""
        print("📈 生成可视化图表...")

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

        # 1. 安全issue严重性分布
        severity_count = analysis_results['severity_count']
        severity_labels = ['高风险', '中风险', '低风险', '未知']
        severity_values = [severity_count['high'], severity_count['medium'],
                          severity_count['low'], severity_count['unknown']]
        severity_colors = ['#ff4444', '#ffaa00', '#ffff44', '#aaaaaa']

        if sum(severity_values) > 0:
            ax1.pie(severity_values, labels=severity_labels, colors=severity_colors, autopct='%1.1f%%')
        else:
            ax1.text(0.5, 0.5, '无安全issues', ha='center', va='center', fontsize=12)
        ax1.set_title('安全Issue严重性分布', fontsize=14)

        # 2. 安全issue占比
        total_issues = analysis_results['total_issues']
        security_issues = len(analysis_results['security_issues'])
        non_security = total_issues - security_issues

        ax2.bar(['安全问题', '非安全问题'], [security_issues, non_security],
                color=['#ff6666', '#66b3ff'])
        ax2.set_title(f'安全Issue占比 (总计: {total_issues})', fontsize=14)
        ax2.set_ylabel('数量', fontsize=12)

        # 3. Issue趋势
        if trend_data:
            months = [item['month'] for item in trend_data]
            opened = [item['opened'] for item in trend_data]
            closed = [item['closed'] for item in trend_data]

            x = range(len(months))
            ax3.plot(x, opened, marker='o', label='新建', color='#ff6666')
            ax3.plot(x, closed, marker='s', label='关闭', color='#66b3ff')
            ax3.set_title('Issue趋势分析', fontsize=14)
            ax3.set_xlabel('月份', fontsize=12)
            ax3.set_ylabel('数量', fontsize=12)
            ax3.legend()
            ax3.set_xticks(x)
            ax3.set_xticklabels(months, rotation=45)
        else:
            ax3.text(0.5, 0.5, '无趋势数据', ha='center', va='center', fontsize=12)
            ax3.set_title('Issue趋势分析', fontsize=14)

        # 4. 安全issue状态分布
        security_issues = analysis_results['security_issues']
        state_count = {'open': 0, 'closed': 0, 'other': 0}

        for issue in security_issues:
            if issue['state'] == 'open':
                state_count['open'] += 1
            elif issue['state'] == 'closed':
                state_count['closed'] += 1
            else:
                state_count['other'] += 1

        ax4.bar(['开放中', '已关闭', '其他'],
                [state_count['open'], state_count['closed'], state_count['other']],
                color=['#ff6666', '#66b3ff', '#ffaa00'])
        ax4.set_title('安全Issue状态分布', fontsize=14)
        ax4.set_ylabel('数量', fontsize=12)

        plt.tight_layout()

        # 保存图表
        chart_path = os.path.join(self.output_dir, "github_issue_analysis_v2.png")
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"✅ 可视化图表已保存: {chart_path}")


# def main():
#     """主函数 - 演示使用"""
#     print("🚀 GitHub Issue 安全分析工具 (PyGithub版本)")
#     print("=" * 60)

#     # 示例：分析一个开源项目
#     analyzer = GitHubIssueAnalyzer(
#         repo_owner="Neutree",
#         repo_name="COMTool",
#         output_dir="github_analysis",
#         token=None  # 可以设置GitHub token以提高API限制
#     )

#     try:
#         # 获取issues
#         issues = analyzer.get_issues(days_back=360)  # 最近3个月

#         if not issues:
#             print("⚠️  没有找到issues")
#             return

#         # 分析安全issues
#         analysis_results = analyzer.analyze_security_issues(issues)

#         # 分析趋势
#         trend_data = analyzer.analyze_issue_trends(issues)

#         # 保存结果
#         analyzer.save_results(analysis_results, trend_data)

#         # 可视化
#         analyzer.visualize_results(analysis_results, trend_data)

#         print("\n🎉 分析完成!")

#     except Exception as e:
#         print(f"❌ 分析失败: {str(e)}")


# if __name__ == "__main__":
#     main()