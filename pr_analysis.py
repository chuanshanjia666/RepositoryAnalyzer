import os
import time
import pandas as pd
import matplotlib.pyplot as plt
from github import Github
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载环境变量（存储GitHub Token）
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("请在.env文件中配置GITHUB_TOKEN（GitHub个人访问令牌）")

# 初始化GitHub客户端
g = Github(GITHUB_TOKEN)

class PRAnalyzer:
    def __init__(self, repo_full_name, days_threshold=7):
        """
        初始化PR分析器
        :param repo_full_name: 仓库全名（如 "octocat/hello-world"）
        :param days_threshold: 僵尸PR的时间阈值（天）
        """
        self.repo = g.get_repo(repo_full_name)
        self.days_threshold = days_threshold
        self.pr_data = []  # 存储PR原始数据
        self.analysis_result = {}  # 存储分析结果

    def fetch_pr_data(self):
        """抓取PR全量数据（分页处理，避免API限制）"""
        print(f"开始抓取仓库 {self.repo.full_name} 的PR数据...")
        # 抓取所有状态的PR（open/closed/merged）
        prs = self.repo.get_pulls(state="all", sort="created", direction="desc")
        
        # 分页遍历（GitHub API单页最多30条）
        for pr in prs:
            # 核心字段提取
            pr_info = {
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
            self.pr_data.append(pr_info)
            # 避免API限流（GitHub API速率限制：5000次/小时）
            time.sleep(0.1)
        
        # 转换为DataFrame便于分析
        self.df = pd.DataFrame(self.pr_data)
        print(f"共抓取 {len(self.df)} 条PR数据")

    def calculate_metrics(self):
        """计算核心分析指标"""
        if len(self.df) == 0:
            raise ValueError("无PR数据可分析")
        
        # 1. PR合入率（merged状态视为合入，closed且未merged视为拒绝）
        total_pr = len(self.df)
        merged_pr = len(self.df[self.df["merged_at"].notna()])
        closed_unmerged = len(self.df[(self.df["state"] == "closed") & (self.df["merged_at"].isna())])
        open_pr = len(self.df[self.df["state"] == "open"])
        merge_rate = merged_pr / total_pr if total_pr > 0 else 0
        reject_rate = closed_unmerged / total_pr if total_pr > 0 else 0

        # 2. 僵尸PR占比（open状态且超过阈值天未处理）
        current_time = datetime.now(pr.created_at.tzinfo)  # 统一时区
        self.df["days_since_created"] = self.df["created_at"].apply(
            lambda x: (current_time - x).days if x else None
        )
        zombie_pr = len(self.df[(self.df["state"] == "open") & (self.df["days_since_created"] > self.days_threshold)])
        zombie_pr_rate = zombie_pr / total_pr if total_pr > 0 else 0

        # 3. 平均审核时长（仅合入的PR）
        merged_df = self.df[self.df["merged_at"].notna()].copy()
        merged_df["review_duration_hours"] = merged_df.apply(
            lambda row: (row["merged_at"] - row["created_at"]).total_seconds() / 3600, axis=1
        )
        avg_review_hours = merged_df["review_duration_hours"].mean()
        # 过滤异常值（如超过30天的审核时长）
        avg_review_hours_filtered = merged_df[merged_df["review_duration_hours"] < 24*30]["review_duration_hours"].mean()

        # 4. 平均评论数（含普通评论+评审评论）
        self.df["total_comments"] = self.df["comments_count"] + self.df["review_comments_count"]
        avg_comments = self.df["total_comments"].mean()

        # 汇总结果
        self.analysis_result = {
            "total_pr": total_pr,
            "open_pr": open_pr,
            "merged_pr": merged_pr,
            "closed_unmerged": closed_unmerged,
            "merge_rate": round(merge_rate * 100, 2),
            "reject_rate": round(reject_rate * 100, 2),
            "zombie_pr_count": zombie_pr,
            "zombie_pr_rate": round(zombie_pr_rate * 100, 2),
            "avg_review_hours": round(avg_review_hours, 2),
            "avg_review_hours_filtered": round(avg_review_hours_filtered, 2),
            "avg_comments": round(avg_comments, 2)
        }

    def generate_visualization(self, save_path="pr_analysis_report.png"):
        """生成可视化报告"""
        plt.rcParams["font.sans-serif"] = ["SimHei"]  # 支持中文
        plt.rcParams["axes.unicode_minus"] = False

        # 创建2x2子图
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f"GitHub仓库PR分析报告 - {self.repo.full_name}", fontsize=16, fontweight="bold")

        # 1. PR状态分布（饼图）
        status_data = [
            self.analysis_result["merged_pr"],
            self.analysis_result["closed_unmerged"],
            self.analysis_result["open_pr"]
        ]
        status_labels = [f"合入({self.analysis_result['merge_rate']}%)", f"拒绝({self.analysis_result['reject_rate']}%)", f"未处理({self.analysis_result['open_pr']})"]
        ax1.pie(status_data, labels=status_labels, autopct="%1.1f%%", startangle=90)
        ax1.set_title("PR状态分布")

        # 2. 僵尸PR占比（柱状图）
        ax2.bar(
            ["僵尸PR", "正常PR"],
            [self.analysis_result["zombie_pr_count"], self.analysis_result["total_pr"] - self.analysis_result["zombie_pr_count"]],
            color=["#ff4444", "#22dd22"]
        )
        ax2.set_title(f"僵尸PR分布（阈值：{self.days_threshold}天）")
        ax2.text(0, self.analysis_result["zombie_pr_count"]/2, f"占比：{self.analysis_result['zombie_pr_rate']}%", ha="center")

        # 3. 平均审核时长（对比原始/过滤后）
        ax3.bar(
            ["原始平均", "过滤异常值后"],
            [self.analysis_result["avg_review_hours"], self.analysis_result["avg_review_hours_filtered"]],
            color=["#4488ff", "#44ddff"]
        )
        ax3.set_title("PR平均审核时长（小时）")
        ax3.set_ylabel("时长（小时）")

        # 4. 平均评论数
        ax4.bar(["平均评论数（含评审）"], [self.analysis_result["avg_comments"]], color="#ff8844")
        ax4.set_title("PR平均评论数")
        ax4.text(0, self.analysis_result["avg_comments"]/2, f"{self.analysis_result['avg_comments']} 条", ha="center")

        # 保存图片
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"可视化报告已保存至：{save_path}")

    def generate_text_report(self, save_path="pr_analysis_report.md"):
        """生成Markdown格式的文字报告"""
        report = f"""
# GitHub仓库PR分析报告
**仓库名称**：{self.repo.full_name}  
**分析时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**僵尸PR阈值**：{self.days_threshold}天  

## 核心指标汇总
| 指标                | 数值          |
|---------------------|---------------|
| 总PR数              | {self.analysis_result['total_pr']} |
| 合入PR数            | {self.analysis_result['merged_pr']} |
| 拒绝PR数            | {self.analysis_result['closed_unmerged']} |
| 未处理PR数          | {self.analysis_result['open_pr']} |
| PR合入率            | {self.analysis_result['merge_rate']}% |
| PR拒绝率            | {self.analysis_result['reject_rate']}% |
| 僵尸PR数            | {self.analysis_result['zombie_pr_count']} |
| 僵尸PR占比          | {self.analysis_result['zombie_pr_rate']}% |
| 平均审核时长（小时） | {self.analysis_result['avg_review_hours']} |
| 过滤异常值后审核时长 | {self.analysis_result['avg_review_hours_filtered']} |
| 平均评论数          | {self.analysis_result['avg_comments']} |

## 关键结论
1. 仓库PR合入率为{self.analysis_result['merge_rate']}%，拒绝率为{self.analysis_result['reject_rate']}%，反映代码评审的严格程度；
2. 僵尸PR占比{self.analysis_result['zombie_pr_rate']}%，若占比过高，需关注PR处理效率；
3. 平均审核时长{self.analysis_result['avg_review_hours']}小时，过滤异常值后为{self.analysis_result['avg_review_hours_filtered']}小时，可对比同类项目评估协作效率。
        """
        # 保存报告
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"文字报告已保存至：{save_path}")

    def run(self):
        """一键执行全流程"""
        self.fetch_pr_data()
        self.calculate_metrics()
        self.generate_visualization()
        self.generate_text_report()
        print("\n=== PR分析完成 ===")
        for k, v in self.analysis_result.items():
            print(f"{k}: {v}")

# 示例使用
if __name__ == "__main__":
    # 1. 配置仓库名称（替换为目标仓库）
    REPO_FULL_NAME = "pytorch/pytorch"
    # 2. 初始化分析器
    analyzer = PRAnalyzer(repo_full_name=REPO_FULL_NAME, days_threshold=7)
    # 3. 执行分析
    analyzer.run()
