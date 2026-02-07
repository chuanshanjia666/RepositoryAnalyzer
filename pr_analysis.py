import os
import time
import pandas as pd
import matplotlib.pyplot as plt
from github import Github
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple



class GitHubConfig:
    """GitHub 配置管理类"""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.client = Github(token) if token else Github()


class PRDataFetcher:
    """PR 数据抓取类"""

    def __init__(self, github_client: Github, repo_full_name: str):
        self.github_client = github_client
        self.repo = github_client.get_repo(repo_full_name)
        self.pr_data = []

    def fetch_pr_data(self) -> pd.DataFrame:
        """抓取PR全量数据（分页处理，避免API限制）"""
        print(f"开始抓取仓库 {self.repo.full_name} 的PR数据...")

        prs = self.repo.get_pulls(state="all", sort="created", direction="desc")

        for pr in prs:
            pr_info = self._extract_pr_info(pr)
            self.pr_data.append(pr_info)

            # 避免API限流
            time.sleep(0.1)

        df = pd.DataFrame(self.pr_data)
        print(f"共抓取 {len(df)} 条PR数据")
        return df

    def _extract_pr_info(self, pr) -> Dict:
        """提取PR核心信息"""
        return {
            "number": pr.number,
            "title": pr.title,
            "state": pr.state,
            "created_at": pr.created_at,
            "closed_at": pr.closed_at,
            "merged_at": pr.merged_at,
            "comments_count": pr.comments,
            "review_comments_count": pr.review_comments,
            "creator": pr.user.login,
            "assignee": pr.assignee.login if pr.assignee else None,
            "labels": [label.name for label in pr.labels]
        }


class PRMetricsCalculator:
    """PR 指标计算类"""

    def __init__(self, df: pd.DataFrame, days_threshold: int = 7):
        self.df = df
        self.days_threshold = days_threshold
        self.current_time = datetime.now().replace(tzinfo=None)

    def calculate_all_metrics(self) -> Dict:
        """计算所有核心分析指标"""
        if len(self.df) == 0:
            raise ValueError("无PR数据可分析")

        metrics = {
            "total_pr": len(self.df),
            "open_pr": self._count_open_pr(),
            "merged_pr": self._count_merged_pr(),
            "closed_unmerged": self._count_closed_unmerged(),
        }

        # 计算比率
        total = metrics["total_pr"]
        metrics["merge_rate"] = round((metrics["merged_pr"] / total) * 100, 2) if total > 0 else 0
        metrics["reject_rate"] = round((metrics["closed_unmerged"] / total) * 100, 2) if total > 0 else 0

        # 僵尸PR分析
        metrics.update(self._calculate_zombie_pr_metrics())

        # 审核时长分析
        metrics.update(self._calculate_review_duration_metrics())

        # 评论分析
        metrics["avg_comments"] = self._calculate_avg_comments()

        return metrics

    def _count_open_pr(self) -> int:
        """统计开放状态的PR数量"""
        return len(self.df[self.df["state"] == "open"])

    def _count_merged_pr(self) -> int:
        """统计已合并的PR数量"""
        return len(self.df[self.df["merged_at"].notna()])

    def _count_closed_unmerged(self) -> int:
        """统计关闭但未合并的PR数量"""
        return len(self.df[(self.df["state"] == "closed") & (self.df["merged_at"].isna())])

    def _calculate_zombie_pr_metrics(self) -> Dict:
        """计算僵尸PR相关指标"""
        self.df["days_since_created"] = self.df["created_at"].apply(
            lambda x: (self.current_time - x.replace(tzinfo=None)).days if x else None
        )

        zombie_pr = len(self.df[
            (self.df["state"] == "open") & (self.df["days_since_created"] > self.days_threshold)
        ])

        zombie_rate = round((zombie_pr / len(self.df)) * 100, 2) if len(self.df) > 0 else 0

        return {
            "zombie_pr_count": zombie_pr,
            "zombie_pr_rate": zombie_rate
        }

    def _calculate_review_duration_metrics(self) -> Dict:
        """计算审核时长相关指标"""
        merged_df = self.df[self.df["merged_at"].notna()].copy()

        if len(merged_df) == 0:
            return {
                "avg_review_hours": 0,
                "avg_review_hours_filtered": 0
            }

        merged_df["review_duration_hours"] = merged_df.apply(
            lambda row: (row["merged_at"].replace(tzinfo=None) - row["created_at"].replace(tzinfo=None)).total_seconds() / 3600, axis=1
        )

        avg_review_hours = merged_df["review_duration_hours"].mean()

        # 过滤异常值（超过30天的审核时长）
        filtered_hours = merged_df[merged_df["review_duration_hours"] < 24 * 30]["review_duration_hours"]
        avg_review_hours_filtered = filtered_hours.mean() if len(filtered_hours) > 0 else 0

        return {
            "avg_review_hours": round(avg_review_hours, 2),
            "avg_review_hours_filtered": round(avg_review_hours_filtered, 2)
        }

    def _calculate_avg_comments(self) -> float:
        """计算平均评论数"""
        self.df["total_comments"] = self.df["comments_count"] + self.df["review_comments_count"]
        return round(self.df["total_comments"].mean(), 2)


class PRVisualizer:
    """PR 数据可视化类"""

    def __init__(self, df: pd.DataFrame, metrics: Dict, repo_name: str):
        self.df = df
        self.metrics = metrics
        self.repo_name = repo_name

    def generate_visualization(self, save_path: str = "pr_analysis_report.png"):
        """生成可视化报告"""
        # Standard configuration for Chinese font support
        plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'Arial Unicode MS', 'SimHei', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f"GitHub仓库PR分析报告 - {self.repo_name}", fontsize=16, fontweight="bold")

        self._plot_status_distribution(ax1)
        self._plot_zombie_pr_distribution(ax2)
        self._plot_review_duration(ax3)
        self._plot_avg_comments(ax4)

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"可视化报告已保存至：{save_path}")

    def _plot_status_distribution(self, ax):
        """绘制PR状态分布饼图"""
        status_data = [
            self.metrics["merged_pr"],
            self.metrics["closed_unmerged"],
            self.metrics["open_pr"]
        ]
        status_labels = [
            f"合入({self.metrics['merge_rate']}%)",
            f"拒绝({self.metrics['reject_rate']}%)",
            f"未处理({self.metrics['open_pr']})"
        ]
        ax.pie(status_data, labels=status_labels, autopct="%1.1f%%", startangle=90)
        ax.set_title("PR状态分布")

    def _plot_zombie_pr_distribution(self, ax):
        """绘制僵尸PR分布柱状图"""
        zombie_count = self.metrics["zombie_pr_count"]
        normal_count = self.metrics["total_pr"] - zombie_count

        ax.bar(["僵尸PR", "正常PR"], [zombie_count, normal_count],
               color=["#ff4444", "#22dd22"])
        ax.set_title(f"僵尸PR分布（阈值：7天）")
        ax.text(0, zombie_count / 2, f"占比：{self.metrics['zombie_pr_rate']}%", ha="center")

    def _plot_review_duration(self, ax):
        """绘制平均审核时长对比图"""
        ax.bar(["原始平均", "过滤异常值后"],
               [self.metrics["avg_review_hours"], self.metrics["avg_review_hours_filtered"]],
               color=["#4488ff", "#44ddff"])
        ax.set_title("PR平均审核时长（小时）")
        ax.set_ylabel("时长（小时）")

    def _plot_avg_comments(self, ax):
        """绘制平均评论数柱状图"""
        avg_comments = self.metrics["avg_comments"]
        ax.bar(["平均评论数（含评审）"], [avg_comments], color="#ff8844")
        ax.set_title("PR平均评论数")
        ax.text(0, avg_comments / 2, f"{avg_comments} 条", ha="center")


class PRReportGenerator:
    """PR 报告生成类"""

    def __init__(self, metrics: Dict, repo_name: str, days_threshold: int):
        self.metrics = metrics
        self.repo_name = repo_name
        self.days_threshold = days_threshold

    def generate_text_report(self, save_path: str = "pr_analysis_report.md"):
        """生成Markdown格式的文字报告"""
        report = f"""
# GitHub仓库PR分析报告

**仓库名称**：{self.repo_name}
**分析时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**僵尸PR阈值**：{self.days_threshold}天

## 核心指标汇总

| 指标                | 数值          |
|---------------------|---------------|
| 总PR数              | {self.metrics['total_pr']} |
| 合入PR数            | {self.metrics['merged_pr']} |
| 拒绝PR数            | {self.metrics['closed_unmerged']} |
| 未处理PR数          | {self.metrics['open_pr']} |
| PR合入率            | {self.metrics['merge_rate']}% |
| PR拒绝率            | {self.metrics['reject_rate']}% |
| 僵尸PR数            | {self.metrics['zombie_pr_count']} |
| 僵尸PR占比          | {self.metrics['zombie_pr_rate']}% |
| 平均审核时长（小时） | {self.metrics['avg_review_hours']} |
| 过滤异常值后审核时长 | {self.metrics['avg_review_hours_filtered']} |
| 平均评论数          | {self.metrics['avg_comments']} |

## 关键结论

1. 仓库PR合入率为{self.metrics['merge_rate']}%，拒绝率为{self.metrics['reject_rate']}%，反映代码评审的严格程度
2. 僵尸PR占比{self.metrics['zombie_pr_rate']}%，若占比过高，需关注PR处理效率
3. 平均审核时长{self.metrics['avg_review_hours']}小时，过滤异常值后为{self.metrics['avg_review_hours_filtered']}小时，可对比同类项目评估协作效率
"""

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"文字报告已保存至：{save_path}")


class PRAnalyzer:
    """PR分析器主类"""

    def __init__(self, repo_full_name: str, days_threshold: int = 7, github_token: Optional[str] = None):
        """
        初始化PR分析器

        :param repo_full_name: 仓库全名（如 "octocat/hello-world"）
        :param days_threshold: 僵尸PR的时间阈值（天）
        :param github_token: GitHub访问令牌（可选，公开仓库可不需要）
        """
        self.repo_full_name = repo_full_name
        self.days_threshold = days_threshold
        self.github_config = GitHubConfig(github_token)
        self.df = None
        self.metrics = None

    def run_analysis(self) -> Dict:
        """执行完整的PR分析流程"""
        try:
            # 1. 数据抓取
            fetcher = PRDataFetcher(self.github_config.client, self.repo_full_name)
            self.df = fetcher.fetch_pr_data()

            # 2. 指标计算
            calculator = PRMetricsCalculator(self.df, self.days_threshold)
            self.metrics = calculator.calculate_all_metrics()

            # 3. 生成可视化报告
            visualizer = PRVisualizer(self.df, self.metrics, self.repo_full_name)
            visualizer.generate_visualization()

            # 4. 生成文字报告
            report_generator = PRReportGenerator(self.metrics, self.repo_full_name, self.days_threshold)
            report_generator.generate_text_report()

            # 5. 打印摘要
            self._print_summary()

            return self.metrics

        except Exception as e:
            print(f"❌ PR分析失败: {str(e)}")
            raise

    def _print_summary(self):
        """打印分析结果摘要"""
        print("\n=== PR分析完成 ===")
        for key, value in self.metrics.items():
            print(f"{key}: {value}")


def analyze_pr_repository(repo_full_name: str, days_threshold: int = 7, github_token: Optional[str] = None) -> Dict:
    """
    便捷的PR分析函数

    :param repo_full_name: 仓库全名
    :param days_threshold: 僵尸PR阈值（天）
    :param github_token: GitHub访问令牌（可选）
    :return: 分析结果字典
    """
    analyzer = PRAnalyzer(repo_full_name, days_threshold, github_token)
    return analyzer.run_analysis()


# 示例使用
if __name__ == "__main__":
    # 配置仓库名称
    REPO_FULL_NAME = "pytorch/pytorch"

    # 执行分析
    analyzer = PRAnalyzer(repo_full_name=REPO_FULL_NAME, days_threshold=7)
    results = analyzer.run_analysis()
