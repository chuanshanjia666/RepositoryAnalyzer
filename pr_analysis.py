import os
import time
import json
import pandas as pd
import matplotlib
# matplotlib.use('Agg')  # 必须在导入pyplot前设置后端
import matplotlib.pyplot as plt
from github import Github, GithubException
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import tempfile
import requests
from pathlib import Path
import shutil
import numpy as np
import re
import warnings

# 忽略非关键警告
warnings.filterwarnings("ignore")

@dataclass
class PRAnalyzerConfig:
    """配置类，集中管理所有可配置参数"""
    cache_expiration_hours: int = 24
    retry_wait_base: int = 60
    max_retries: int = 3
    min_sleep_time: float = 1.5
    zombie_threshold_days: int = 7
    outlier_filter_days: int = 30
    max_authors_display: int = 10
    report_save_path: str = "output"
    font_fallback: str = "DejaVu Sans"
    max_api_attempts: int = 5

class GitHubConfig:
    """GitHub 配置管理类，支持多来源token获取（兼容所有pygithub版本）"""
    
    def __init__(self, token: Optional[str] = None, config: PRAnalyzerConfig = None):
        self.config = config or PRAnalyzerConfig()
        # 优先使用传入的token，其次环境变量，最后无认证
        self.token = token or os.getenv("GITHUB_TOKEN")
        
        try:
            # 基础初始化（兼容所有版本）
            if self.token:
                self.client = Github(self.token, retry=3, timeout=15)
            else:
                self.client = Github(retry=3, timeout=15)
                print("⚠️  未配置GitHub token，将使用无认证模式（API配额受限）")
            
            # 手动设置User-Agent（兼容不同版本的Requester实现）
            self._set_user_agent()
                
            # 验证token有效性并获取配额（兼容不同版本的RateLimit对象）
            self._check_rate_limit()
            
        except Exception as e:
            print(f"❌ GitHub token验证失败: {str(e)}")
            raise

    def _set_user_agent(self):
        """兼容不同版本设置User-Agent"""
        user_agent = "PRAnalyzer/2.0 (contact@example.com)"
        try:
            # 尝试新版本的requester设置
            if hasattr(self.client, '_requester'):
                if hasattr(self.client._requester, 'headers'):
                    self.client._requester.headers['User-Agent'] = user_agent
                elif hasattr(self.client._requester, 'session'):
                    self.client._requester.session.headers['User-Agent'] = user_agent
        except:
            try:
                # 尝试旧版本的session设置
                if hasattr(self.client, 'session'):
                    self.client.session.headers['User-Agent'] = user_agent
            except:
                # 忽略设置失败，不影响核心功能
                print("⚠️  无法设置User-Agent，可能影响API访问（非关键错误）")

    def _check_rate_limit(self):
        """兼容不同版本获取API配额信息"""
        try:
            rate_limit = self.client.get_rate_limit()
            
            # 适配不同版本的属性名
            if hasattr(rate_limit, 'core'):
                # 新版本
                remaining = rate_limit.core.remaining
                limit = rate_limit.core.limit
            elif hasattr(rate_limit, 'rate'):
                # 旧版本
                remaining = rate_limit.rate.remaining
                limit = rate_limit.rate.limit
            else:
                # 最兼容的方式（直接从原始数据获取）
                rate_data = self.client.get_rate_limit()._rawData
                remaining = rate_data.get('rate', {}).get('remaining', 0)
                limit = rate_data.get('rate', {}).get('limit', 0)
                
            print(f"📊 当前API配额: {remaining}/{limit}")
            
        except Exception as e:
            # 配额检查失败不影响核心功能，仅警告
            print(f"⚠️  无法获取API配额信息: {str(e)}")

class PRDataFetcher:
    """PR 数据抓取类，增强限流处理、缓存策略和异常处理"""
    
    def __init__(self, github_client: Github, repo_full_name: str, config: PRAnalyzerConfig = None):
        self.github_client = github_client
        self.repo = github_client.get_repo(repo_full_name)
        self.pr_data = []
        self.config = config or PRAnalyzerConfig()
        self.cache_dir = self._get_cache_dir()
        self.current_attempt = 0
        
    def _get_cache_dir(self) -> str:
        """获取缓存目录，优先使用系统临时目录"""
        try:
            temp_dir = tempfile.gettempdir()
            cache_dir = os.path.join(temp_dir, "pr_analyzer_cache")
            os.makedirs(cache_dir, exist_ok=True)
            return cache_dir
        except Exception as e:
            print(f"⚠️  使用系统临时目录失败，改用当前目录: {str(e)}")
            return ".cache"
            
    def _get_cache_file_path(self) -> str:
        """生成缓存文件路径"""
        safe_repo_name = re.sub(r'[^\w]', '_', self.repo.full_name)
        return os.path.join(self.cache_dir, f"{safe_repo_name}_pr_cache")
        
    def _load_from_cache(self) -> pd.DataFrame:
        """从缓存加载数据，支持过期检查"""
        meta_path = f"{self._get_cache_file_path()}.json"
        data_path = f"{self._get_cache_file_path()}.csv"
        
        if not (os.path.exists(meta_path) and os.path.exists(data_path)):
            print("🔍 缓存文件不存在")
            return pd.DataFrame()
            
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
                
            # 检查缓存是否过期
            cache_time = datetime.fromisoformat(meta["timestamp"])
            if datetime.now() - cache_time < timedelta(hours=self.config.cache_expiration_hours):
                print("💾 使用缓存中的PR数据")
                return pd.read_csv(data_path)
            else:
                print("⏰ 缓存已过期，将重新抓取数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 加载缓存失败: {str(e)}")
            return pd.DataFrame()
        
    def _save_to_cache(self, df: pd.DataFrame):
        """保存数据到缓存，使用CSV+JSON组合格式"""
        try:
            meta_path = f"{self._get_cache_file_path()}.json"
            data_path = f"{self._get_cache_file_path()}.csv"
            
            # 保存元数据
            meta = {
                "timestamp": datetime.now().isoformat(),
                "repo": self.repo.full_name,
                "count": len(df)
            }
            
            with open(meta_path, "w") as f:
                json.dump(meta, f)
                
            # 保存数据
            df.to_csv(data_path, index=False)
            print(f"✅ 缓存已保存至 {data_path}")
        except Exception as e:
            print(f"❌ 保存缓存失败: {str(e)}")
            
    def _handle_api_rate_limit(self, exception):
        """处理API限流，动态计算等待时间"""
        if isinstance(exception, GithubException) and exception.status == 403:
            try:
                # 获取剩余配额重置时间
                reset_time = datetime.fromtimestamp(self.github_client.rate_limiting_resettime)
                wait_time = max((reset_time - datetime.now()).total_seconds(), self.config.retry_wait_base)
                print(f"⏳ 达到API限流，等待 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
                self.current_attempt = 0  # 重置尝试计数器
                return True
            except Exception as e:
                print(f"⚠️  动态计算限流等待时间失败，使用默认策略: {str(e)}")
                wait_time = self.config.retry_wait_base * (self.current_attempt + 1)  # 退避策略
                print(f"达到API限流，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                return True
        return False

    def fetch_pr_data(self) -> pd.DataFrame:
        """抓取PR全量数据（优先使用缓存）"""
        # 尝试从缓存加载
        df = self._load_from_cache()
        if not df.empty:
            print(f"💾 从缓存加载到 {len(df)} 条PR数据")
            return df
            
        # 缓存不存在或已过期，重新抓取数据
        print("🔄 开始重新抓取PR数据...")
        
        try:
            # 获取PR列表（分页处理）
            prs = self.repo.get_pulls(state="all", sort="created", direction="desc")
            total_prs = prs.totalCount
            print(f"需要抓取的PR总数: {total_prs}")
            
            # 分批次处理
            batch_size = 100
            for i in range(0, total_prs, batch_size):
                retries = 0
                while retries < self.config.max_api_attempts:
                    try:
                        # 获取当前批次的PR
                        batch_prs = prs.get_page(i // batch_size)
                        
                        for pr in batch_prs:
                            pr_info = self._extract_pr_info(pr)
                            self.pr_data.append(pr_info)
                            
                            # 动态休眠，根据API配额调整
                            self._dynamic_sleep(len(self.pr_data))
                        
                        # 进度显示
                        current = min(i + batch_size, total_prs)
                        print(f"已抓取 {current}/{total_prs} 个PR")
                        
                        break  # 成功获取批次数据，退出重试循环
                        
                    except GithubException as e:
                        if self._handle_api_rate_limit(e):
                            retries += 1
                            continue
                        else:
                            print(f"抓取PR时发生GitHub错误: {str(e)}")
                            time.sleep(5)
                            break
                    except Exception as e:
                        print(f"抓取PR时发生未知错误: {str(e)}")
                        time.sleep(5)
                        break

            df = pd.DataFrame(self.pr_data)
            print(f"共抓取 {len(df)} 条PR数据")
            
            # 保存到缓存
            self._save_to_cache(df)
            
            return df
            
        except GithubException as e:
            print(f"获取PR列表时发生GitHub错误: {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            print(f"获取PR列表时发生未知错误: {str(e)}")
            return pd.DataFrame()

    def _dynamic_sleep(self, current_count: int):
        """动态休眠策略，根据API配额和当前进度调整"""
        try:
            # 每抓取100个PR检查一次配额
            if current_count % 100 == 0:
                rate_limit = self.github_client.get_rate_limit()
                if hasattr(rate_limit, 'core'):
                    remaining = rate_limit.core.remaining
                    limit = rate_limit.core.limit
                else:
                    rate_data = self.github_client.get_rate_limit()._rawData
                    remaining = rate_data.get('rate', {}).get('remaining', 0)
                    limit = rate_data.get('rate', {}).get('limit', 0)
                
                usage_ratio = 1 - (remaining / limit)
                
                # 根据使用率调整休眠时间
                if usage_ratio > 0.8:
                    sleep_time = self.config.min_sleep_time * 3
                elif usage_ratio > 0.5:
                    sleep_time = self.config.min_sleep_time * 2
                else:
                    sleep_time = self.config.min_sleep_time
                    
                print(f"API使用率: {usage_ratio*100:.1f}%, 休眠时间: {sleep_time:.1f}s")
                time.sleep(sleep_time)
            else:
                time.sleep(self.config.min_sleep_time)
                
        except Exception as e:
            print(f"动态休眠策略失败，使用默认休眠时间: {str(e)}")
            time.sleep(self.config.min_sleep_time)

    def _extract_pr_info(self, pr) -> Dict:
        """提取PR核心信息，增强时间戳处理和异常处理"""
        try:
            pr_info = {
                "number": pr.number,
                "title": pr.title.replace('\n', ' ').replace('\r', '') if pr.title else "",
                "state": pr.state,
                "created_at": pr.created_at.replace(tzinfo=None) if pr.created_at else None,
                "closed_at": pr.closed_at.replace(tzinfo=None) if pr.closed_at else None,
                "merged_at": pr.merged_at.replace(tzinfo=None) if pr.merged_at else None,
                "comments_count": pr.comments,
                "review_comments_count": pr.review_comments,
                "commits_count": pr.commits,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "creator": pr.user.login if pr.user else "unknown",
                "assignee": pr.assignee.login if pr.assignee else None,
                "labels": [label.name for label in pr.labels] if pr.labels else [],
                "base_branch": pr.base.ref if pr.base else "",
                "head_branch": pr.head.ref if pr.head else "",
                "is_merged": pr.merged
            }
            
            # 验证时间戳有效性（考虑系统时间错误的情况）
            current_time = datetime.now()
            if pr_info["created_at"] and (pr_info["created_at"] > current_time):
                print(f"PR {pr.number} 创建时间未来时间，已修正")
                pr_info["created_at"] = None
                
            if pr_info["merged_at"] and pr_info["created_at"] and (pr_info["merged_at"] < pr_info["created_at"]):
                print(f"PR {pr.number} 合并时间早于创建时间，已修正")
                pr_info["merged_at"] = None
                
            return pr_info
        except Exception as e:
            print(f"PR信息提取失败: {str(e)}")
            return {}


class PRMetricsCalculator:
    """PR 指标计算类，增强异常处理和指标丰富度"""
    
    def __init__(self, df: pd.DataFrame, config: PRAnalyzerConfig = None):
        self.df = df.copy()
        self.config = config or PRAnalyzerConfig()
        self.current_time = datetime.now().replace(tzinfo=None)
        self._preprocess_data()

    def _preprocess_data(self):
        """预处理数据，增强数据质量"""
        # 处理缺失值
        self.df["comments_count"] = self.df["comments_count"].fillna(0).astype(int)
        self.df["review_comments_count"] = self.df["review_comments_count"].fillna(0).astype(int)
        self.df["commits_count"] = self.df["commits_count"].fillna(0).astype(int)
        self.df["additions"] = self.df["additions"].fillna(0).astype(int)
        self.df["deletions"] = self.df["deletions"].fillna(0).astype(int)
        self.df["changed_files"] = self.df["changed_files"].fillna(0).astype(int)
        self.df["created_at"] = pd.to_datetime(self.df["created_at"], errors='coerce')
        self.df["closed_at"] = pd.to_datetime(self.df["closed_at"], errors='coerce')
        self.df["merged_at"] = pd.to_datetime(self.df["merged_at"], errors='coerce')
        
        # 计算活跃时间
        self.df["days_since_created"] = self.df["created_at"].apply(
            lambda x: (self.current_time - x).days if pd.notna(x) and x < self.current_time else None
        )
        self.df["is_zombie"] = (self.df["state"] == "open") & (self.df["days_since_created"] > self.config.zombie_threshold_days)
        self.df["total_comments"] = self.df["comments_count"] + self.df["review_comments_count"]

    def calculate_all_metrics(self) -> Dict:
        """计算所有核心分析指标，增强空数据处理"""
        metrics = {
            "total_pr": 0,
            "open_pr": 0,
            "merged_pr": 0,
            "closed_unmerged": 0,
            "merge_rate": 0.0,
            "reject_rate": 0.0,
            "zombie_pr_count": 0,
            "zombie_pr_rate": 0.0,
            "avg_review_hours": 0.0,
            "avg_review_hours_filtered": 0.0,
            "median_review_hours": 0.0,
            "avg_comments": 0.0,
            "avg_commits": 0.0,
            "avg_code_changes": {
                "additions": 0,
                "deletions": 0,
                "changed_files": 0
            },
            "pr_per_author": {},
            "pr_by_label": {},
            "time_to_close": 0.0,
            "pr_lifetime_distribution": {},
            "branch_analysis": {}
        }
        
        if len(self.df) == 0:
            print("无PR数据可分析")
            return metrics

        try:
            metrics["total_pr"] = len(self.df)
            metrics["open_pr"] = self._count_open_pr()
            metrics["merged_pr"] = self._count_merged_pr()
            metrics["closed_unmerged"] = self._count_closed_unmerged()
            
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
            
            # 提交分析
            metrics.update(self._calculate_commit_metrics())
            
            # PR作者分析
            metrics["pr_per_author"] = self._calculate_pr_per_author()
            
            # PR标签分析
            metrics["pr_by_label"] = self._calculate_pr_by_label()
            
            # 分支分析
            metrics["branch_analysis"] = self._calculate_branch_analysis()
            
            # PR生命周期分析
            metrics.update(self._calculate_pr_lifecycle_metrics())
            
            return metrics
            
        except Exception as e:
            print(f"指标计算失败: {str(e)}")
            return metrics

    def _count_open_pr(self) -> int:
        """统计开放状态的PR数量"""
        try:
            return len(self.df[self.df["state"] == "open"])
        except Exception as e:
            print(f"统计开放PR失败: {str(e)}")
            return 0

    def _count_merged_pr(self) -> int:
        """统计已合并的PR数量"""
        try:
            return len(self.df[self.df["merged_at"].notna()])
        except Exception as e:
            print(f"统计已合并PR失败: {str(e)}")
            return 0

    def _count_closed_unmerged(self) -> int:
        """统计关闭但未合并的PR数量"""
        try:
            return len(self.df[(self.df["state"] == "closed") & (self.df["merged_at"].isna())])
        except Exception as e:
            print(f"统计未合并关闭PR失败: {str(e)}")
            return 0

    def _calculate_zombie_pr_metrics(self) -> Dict:
        """计算僵尸PR相关指标"""
        try:
            zombie_pr = len(self.df[self.df["is_zombie"]])
            zombie_rate = round((zombie_pr / len(self.df)) * 100, 2) if len(self.df) > 0 else 0

            return {
                "zombie_pr_count": zombie_pr,
                "zombie_pr_rate": zombie_rate
            }
        except Exception as e:
            print(f"僵尸PR计算失败: {str(e)}")
            return {"zombie_pr_count": 0, "zombie_pr_rate": 0}

    def _calculate_review_duration_metrics(self) -> Dict:
        """计算审核时长相关指标"""
        try:
            # 过滤已合并的PR
            merged_df = self.df[self.df["merged_at"].notna()].copy()
            
            if len(merged_df) == 0:
                return {
                    "avg_review_hours": 0,
                    "avg_review_hours_filtered": 0,
                    "median_review_hours": 0
                }

            # 计算审核时长
            merged_df["review_duration_hours"] = merged_df.apply(
                lambda row: (row["merged_at"] - row["created_at"]).total_seconds() / 3600 
                if pd.notna(row["merged_at"]) and pd.notna(row["created_at"]) and row["merged_at"] > row["created_at"] 
                else 0, 
                axis=1
            )

            avg_review_hours = merged_df["review_duration_hours"].mean()
            median_review_hours = merged_df["review_duration_hours"].median()

            # 过滤异常值（超过配置阈值的审核时长）
            max_hours = self.config.outlier_filter_days * 24
            filtered_hours = merged_df[merged_df["review_duration_hours"] < max_hours]["review_duration_hours"]
            avg_review_hours_filtered = filtered_hours.mean() if len(filtered_hours) > 0 else 0

            return {
                "avg_review_hours": round(avg_review_hours, 2),
                "avg_review_hours_filtered": round(avg_review_hours_filtered, 2),
                "median_review_hours": round(median_review_hours, 2)
            }
        except Exception as e:
            print(f"审核时长计算失败: {str(e)}")
            return {
                "avg_review_hours": 0,
                "avg_review_hours_filtered": 0,
                "median_review_hours": 0
            }

    def _calculate_avg_comments(self) -> float:
        """计算平均评论数"""
        try:
            avg_comments = self.df["total_comments"].mean()
            return round(avg_comments, 2) if not pd.isna(avg_comments) else 0
        except Exception as e:
            print(f"平均评论数计算失败: {str(e)}")
            return 0

    def _calculate_commit_metrics(self) -> Dict:
        """计算提交相关指标"""
        try:
            avg_commits = self.df["commits_count"].mean()
            avg_additions = self.df["additions"].mean()
            avg_deletions = self.df["deletions"].mean()
            avg_files = self.df["changed_files"].mean()
            
            return {
                "avg_commits": round(avg_commits, 2),
                "avg_code_changes": {
                    "additions": round(avg_additions, 2),
                    "deletions": round(avg_deletions, 2),
                    "changed_files": round(avg_files, 2)
                }
            }
        except Exception as e:
            print(f"提交指标计算失败: {str(e)}")
            return {
                "avg_commits": 0,
                "avg_code_changes": {
                    "additions": 0,
                    "deletions": 0,
                    "changed_files": 0
                }
            }

    def _calculate_pr_per_author(self) -> Dict:
        """统计各作者的PR数量"""
        try:
            author_counts = self.df["creator"].value_counts().to_dict()
            return {author: int(count) for author, count in author_counts.items()}
        except Exception as e:
            print(f"PR作者统计失败: {str(e)}")
            return {}

    def _calculate_pr_by_label(self) -> Dict:
        """统计各标签的PR数量"""
        try:
            # 展开标签列表
            all_labels = []
            for labels in self.df["labels"]:
                if isinstance(labels, list) and labels:
                    all_labels.extend(labels)
                else:
                    all_labels.append("无标签")
                    
            from collections import Counter
            label_counts = Counter(all_labels)
            return dict(label_counts)
        except Exception as e:
            print(f"PR标签统计失败: {str(e)}")
            return {}

    def _calculate_branch_analysis(self) -> Dict:
        """分析PR的分支分布"""
        try:
            base_branches = self.df["base_branch"].value_counts().to_dict()
            head_branches = self.df["head_branch"].value_counts().to_dict()
            
            return {
                "base_branches": {branch: int(count) for branch, count in base_branches.items()},
                "head_branches": {branch: int(count) for branch, count in head_branches.items()}
            }
        except Exception as e:
            print(f"分支分析失败: {str(e)}")
            return {"base_branches": {}, "head_branches": {}}

    def _calculate_pr_lifecycle_metrics(self) -> Dict:
        """计算PR生命周期相关指标"""
        try:
            # 计算关闭PR的生命周期
            closed_df = self.df[self.df["closed_at"].notna()].copy()
            if len(closed_df) == 0:
                return {
                    "time_to_close": 0,
                    "pr_lifetime_distribution": {}
                }
                
            closed_df["lifetime_days"] = (closed_df["closed_at"] - closed_df["created_at"]).dt.days
            avg_lifetime = closed_df["lifetime_days"].mean()
            
            # 计算分布
            bins = [0, 1, 3, 7, 14, 30, 60, float('inf')]
            labels = ["<1天", "1-3天", "3-7天", "7-14天", "14-30天", "30-60天", ">60天"]
            distribution = pd.cut(closed_df["lifetime_days"], bins=bins, labels=labels, include_lowest=True)
            distribution_counts = distribution.value_counts().sort_index()
            
            return {
                "time_to_close": round(avg_lifetime, 2),
                "pr_lifetime_distribution": dict(distribution_counts.astype(int))
            }
        except Exception as e:
            print(f"PR生命周期计算失败: {str(e)}")
            return {
                "time_to_close": 0,
                "pr_lifetime_distribution": {}
            }


class PRVisualizer:
    """PR 数据可视化类，增强中文化支持和图表质量"""

    def __init__(self, df: pd.DataFrame, metrics: Dict, repo_name: str, config: PRAnalyzerConfig = None):
        self.df = df
        self.metrics = metrics
        self.repo_name = repo_name
        self.config = config or PRAnalyzerConfig()
        self._setup_chinese_font()

    def _setup_chinese_font(self):
        """设置中文显示支持，尝试多种字体"""
        try:
            plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            # # 尝试检测系统可用字体
            # available_fonts = matplotlib.font_manager.findSystemFonts()
            # font_names = [matplotlib.font_manager.FontProperties(fname=fname).get_name() for fname in available_fonts]
            
            # # 优先选择常见中文字体
            # chinese_fonts = [
            #     'SimHei', 'FangSong', 'KaiTi', 'Microsoft YaHei',
            #     'Source Han Sans CN', 'Arial Unicode MS', 'sans-serif'
            # ]
            
            # # 选择第一个可用字体
            # for font in chinese_fonts:
            #     if font in font_names:
            #         plt.rcParams['font.sans-serif'] = [font]
            #         plt.rcParams['axes.unicode_minus'] = False
            #         print(f"使用中文字体: {font}")
            #         return
            
            # # 如果没有可用中文字体，使用备用字体
            # plt.rcParams['font.sans-serif'] = [self.config.font_fallback]
            # plt.rcParams['axes.unicode_minus'] = False
            # print(f"使用备用字体: {self.config.font_fallback}")
            
        except Exception as e:
            print(f"中文字体设置失败: {str(e)}")

    def generate_visualization(self, save_path: str = "pr_analysis_report.png"):
        """生成可视化报告"""
        try:
            # 设置图表样式
            plt.style.use('ggplot')
            
            # 创建输出目录
            os.makedirs(os.path.dirname(save_path) or self.config.report_save_path, exist_ok=True)
            
            # 调整图表尺寸和布局
            fig, axes = plt.subplots(3, 2, figsize=(24, 30))
            fig.suptitle(f"GitHub仓库PR分析报告 - {self.repo_name}", fontsize=24, fontweight="bold", y=0.95)

            # 重新组织图表布局
            self._plot_status_distribution(axes[0, 0])
            self._plot_zombie_pr_distribution(axes[0, 1])
            self._plot_review_duration(axes[1, 0])
            self._plot_code_changes(axes[1, 1])
            self._plot_pr_per_author(axes[2, 0])
            self._plot_pr_lifetime_distribution(axes[2, 1])

            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"可视化报告已保存至：{save_path}")
            
        except Exception as e:
            print(f"可视化生成失败: {str(e)}")
        finally:
            plt.close()

    def _plot_status_distribution(self, ax):
        """绘制PR状态分布饼图"""
        try:
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
            
            # 使用更柔和的颜色
            colors = ['#4CAF50', '#F44336', '#2196F3']
            
            ax.pie(status_data, labels=status_labels, autopct="%1.1f%%", 
                  startangle=90, colors=colors, wedgeprops={'edgecolor': 'black'})
            ax.set_title("PR状态分布", fontsize=16, pad=20)
            
            # 添加图例
            ax.legend(status_labels, loc="best", bbox_to_anchor=(0.5, 0, 0.5, 0.5))
        except Exception as e:
            print(f"状态分布图绘制失败: {str(e)}")

    def _plot_zombie_pr_distribution(self, ax):
        """绘制僵尸PR分布柱状图"""
        try:
            zombie_count = self.metrics["zombie_pr_count"]
            normal_count = self.metrics["total_pr"] - zombie_count

            bars = ax.bar(["僵尸PR", "正常PR"], [zombie_count, normal_count],
                         color=["#ff4444", "#22dd22"], edgecolor='black')
            ax.set_title(f"僵尸PR分布（阈值：{self.config.zombie_threshold_days}天）", fontsize=16, pad=20)
            ax.text(0, zombie_count / 2, f"占比：{self.metrics['zombie_pr_rate']}%", 
                   ha="center", fontsize=12, color='white', fontweight='bold')
            
            # 添加数据标签
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, height + 0.5, 
                       f'{int(height)}', ha='center', fontsize=10)
        except Exception as e:
            print(f"僵尸PR分布图绘制失败: {str(e)}")

    def _plot_review_duration(self, ax):
        """绘制平均审核时长对比图"""
        try:
            values = [
                self.metrics["avg_review_hours"], 
                self.metrics["median_review_hours"],
                self.metrics["avg_review_hours_filtered"]
            ]
            labels = ["原始平均", "中位数", "过滤异常值后"]
            
            bars = ax.bar(labels, values, color=['#4488ff', '#ff8844', '#44ddff'], edgecolor='black')
            ax.set_title("PR平均审核时长（小时）", fontsize=16, pad=20)
            ax.set_ylabel("时长（小时）", fontsize=14)
            
            # 添加数据标签
            for i, v in enumerate(values):
                ax.text(i, v + 0.5, str(v), ha='center', fontsize=10)
                
            # 添加参考线
            avg_filtered = self.metrics["avg_review_hours_filtered"]
            if avg_filtered > 0:
                ax.axhline(y=avg_filtered, color='r', linestyle='--', alpha=0.5)
                ax.text(len(values)-0.5, avg_filtered, f'过滤均值: {avg_filtered}', 
                       color='red', va='center')
        except Exception as e:
            print(f"审核时长图绘制失败: {str(e)}")

    def _plot_code_changes(self, ax):
        """绘制代码变更统计"""
        try:
            code_changes = self.metrics["avg_code_changes"]
            
            labels = ['新增代码', '删除代码', '修改文件']
            values = [code_changes["additions"], code_changes["deletions"], code_changes["changed_files"]]
            
            bars = ax.bar(labels, values, color=['#4CAF50', '#F44336', '#2196F3'], edgecolor='black')
            ax.set_title("平均代码变更统计", fontsize=16, pad=20)
            ax.set_ylabel("数量", fontsize=14)
            
            # 添加数据标签
            for i, v in enumerate(values):
                ax.text(i, v + 0.5, str(v), ha='center', fontsize=10)
                
        except Exception as e:
            print(f"代码变更统计图绘制失败: {str(e)}")

    def _plot_pr_per_author(self, ax):
        """绘制PR作者分布图"""
        try:
            author_data = self.metrics.get("pr_per_author", {})
            if not author_data:
                ax.text(0.5, 0.5, "无数据", ha='center', va='center')
                ax.set_title("PR作者分布", fontsize=16, pad=20)
                return
                
            # 只显示前10名作者
            top_authors = dict(sorted(author_data.items(), key=lambda x: x[1], reverse=True)[:self.config.max_authors_display])
            
            authors = list(top_authors.keys())
            counts = list(top_authors.values())
            
            bars = ax.barh(authors, counts, color="#55aacc", edgecolor='black')
            ax.set_title(f"PR作者分布（前{self.config.max_authors_display}名）", fontsize=16, pad=20)
            ax.set_xlabel("PR数量", fontsize=14)
            
            # 添加数据标签
            for i, v in enumerate(counts):
                ax.text(v + 0.2, i, str(v), va='center', fontsize=10)
                
            ax.invert_yaxis()  # 从上到下按数量递减排序
            ax.grid(axis='x', linestyle='--', alpha=0.7)
        except Exception as e:
            print(f"PR作者分布图绘制失败: {str(e)}")

    def _plot_pr_lifetime_distribution(self, ax):
        """绘制PR生命周期分布"""
        try:
            lifetime_data = self.metrics.get("pr_lifetime_distribution", {})
            if not lifetime_data:
                ax.text(0.5, 0.5, "无数据", ha='center', va='center')
                ax.set_title("PR生命周期分布", fontsize=16, pad=20)
                return
                
            labels = list(lifetime_data.keys())
            counts = list(lifetime_data.values())
            
            bars = ax.bar(labels, counts, color="#aacc55", edgecolor='black')
            ax.set_title("PR生命周期分布（关闭PR）", fontsize=16, pad=20)
            ax.set_ylabel("数量", fontsize=14)
            
            # 添加数据标签
            for i, v in enumerate(counts):
                ax.text(i, v + 0.2, str(v), ha='center', fontsize=10)
                
            # 旋转x轴标签
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            ax.grid(axis='y', linestyle='--', alpha=0.7)
        except Exception as e:
            print(f"PR生命周期分布图绘制失败: {str(e)}")


class PRReportGenerator:
    """PR 报告生成类，增强分析结论和输出格式"""

    def __init__(self, metrics: Dict, repo_name: str, config: PRAnalyzerConfig = None):
        self.metrics = metrics
        self.repo_name = repo_name
        self.config = config or PRAnalyzerConfig()

    def generate_text_report(self, save_path: str = "pr_analysis_report.md"):
        """生成Markdown格式的文字报告"""
        try:
            # 创建输出目录
            os.makedirs(os.path.dirname(save_path) or self.config.report_save_path, exist_ok=True)
            
            report = f"""
# GitHub仓库PR分析报告

**仓库名称**：{self.repo_name}
**分析时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**僵尸PR阈值**：{self.config.zombie_threshold_days}天
**异常值过滤阈值**：{self.config.outlier_filter_days}天

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
| 中位数审核时长（小时） | {self.metrics['median_review_hours']} |
| 过滤异常值后审核时长 | {self.metrics['avg_review_hours_filtered']} |
| 平均评论数          | {self.metrics['avg_comments']} |
| 平均提交次数        | {self.metrics['avg_commits']} |
| 平均新增代码        | {self.metrics['avg_code_changes']['additions']} 行 |
| 平均删除代码        | {self.metrics['avg_code_changes']['deletions']} 行 |
| 平均修改文件数      | {self.metrics['avg_code_changes']['changed_files']} 个 |
| 平均生命周期（天）  | {self.metrics.get('time_to_close', 0)} |

## 关键结论

1. **PR处理效率**：仓库PR合入率为{self.metrics['merge_rate']}%，拒绝率为{self.metrics['reject_rate']}%，反映代码评审的严格程度。{'偏高' if self.metrics['reject_rate'] > 50 else '正常'}的拒绝率可能表明评审标准较为严格。
2. **僵尸PR情况**：僵尸PR占比{self.metrics['zombie_pr_rate']}%，{'过高' if self.metrics['zombie_pr_rate'] > 20 else '正常'}的比例表明需要关注PR处理效率。
3. **审核效率**：平均审核时长{self.metrics['avg_review_hours']}小时，中位数为{self.metrics['median_review_hours']}小时。过滤异常值后为{self.metrics['avg_review_hours_filtered']}小时，{'较长' if self.metrics['avg_review_hours_filtered'] > 72 else '正常'}的时长可能影响开发效率。
4. **代码质量**：平均每次PR新增代码{self.metrics['avg_code_changes']['additions']}行，删除代码{self.metrics['avg_code_changes']['deletions']}行，修改文件{self.metrics['avg_code_changes']['changed_files']}个。{'较大规模的修改' if self.metrics['avg_code_changes']['changed_files'] > 10 else '较小规模的修改'}可能增加评审难度。
5. **PR生命周期**：关闭PR的平均生命周期为{self.metrics.get('time_to_close', 0)}天，{'较长' if self.metrics.get('time_to_close', 0) > 14 else '正常'}的生命周期可能表明评审流程需要优化。
6. **协作模式**：PR的平均评论数为{self.metrics['avg_comments']}条，{'丰富' if self.metrics['avg_comments'] > 10 else '较少'}的评论表明团队协作程度较高。
7. **提交习惯**：平均每次PR提交次数为{self.metrics['avg_commits']}次，{'较多' if self.metrics['avg_commits'] > 5 else '正常'}的提交次数可能表明开发过程较为迭代。

## 详细分析

### PR作者分布
{self._generate_author_analysis()}

### PR标签分布
{self._generate_label_analysis()}

### PR分支分析
{self._generate_branch_analysis()}

### PR生命周期分布
{self._generate_lifetime_analysis()}

---

*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(report)

            print(f"文字报告已保存至：{save_path}")
        except Exception as e:
            print(f"文字报告生成失败: {str(e)}")

    def _generate_author_analysis(self) -> str:
        """生成PR作者分析部分"""
        try:
            author_data = self.metrics.get("pr_per_author", {})
            if not author_data:
                return "无作者数据可分析"
                
            # 排序并计算总PR数
            authors = sorted(author_data.items(), key=lambda x: x[1], reverse=True)
            total = sum(author_data.values())
            
            # 生成Markdown表格
            table_rows = []
            for author, count in authors[:self.config.max_authors_display]:  # 前N名
                percentage = (count / total) * 100
                table_rows.append(f"| {author} | {count} | {percentage:.1f}% |")
                
            table = "| 作者 | PR数量 | 占比 |\n|------|--------|------|\n" + "\n".join(table_rows)
            
            return table
        except Exception as e:
            print(f"作者分析生成失败: {str(e)}")
            return ""

    def _generate_label_analysis(self) -> str:
        """生成PR标签分析部分"""
        try:
            label_data = self.metrics.get("pr_by_label", {})
            if not label_data:
                return "无标签数据可分析"
                
            # 排序并计算总PR数
            labels = sorted(label_data.items(), key=lambda x: x[1], reverse=True)
            total = sum(label_data.values())
            
            # 生成Markdown表格
            table_rows = []
            for label, count in labels[:self.config.max_authors_display]:  # 前N名
                percentage = (count / total) * 100
                table_rows.append(f"| {label} | {count} | {percentage:.1f}% |")
                
            table = "| 标签 | PR数量 | 占比 |\n|------|--------|------|\n" + "\n".join(table_rows)
            
            return table
        except Exception as e:
            print(f"标签分析生成失败: {str(e)}")
            return ""

    def _generate_branch_analysis(self) -> str:
        """生成PR分支分析部分"""
        try:
            branch_data = self.metrics.get("branch_analysis", {})
            if not branch_data:
                return "无分支数据可分析"
                
            # 分析目标分支
            base_branches = branch_data.get("base_branches", {})
            if base_branches:
                base_table = "| 分支 | PR数量 |\n|------|--------|\n"
                for branch, count in sorted(base_branches.items(), key=lambda x: x[1], reverse=True):
                    base_table += f"| {branch} | {count} |\n"
            else:
                base_table = "无目标分支数据"
                
            # 分析来源分支
            head_branches = branch_data.get("head_branches", {})
            if head_branches:
                head_table = "| 分支 | PR数量 |\n|------|--------|\n"
                for branch, count in sorted(head_branches.items(), key=lambda x: x[1], reverse=True):
                    head_table += f"| {branch} | {count} |\n"
            else:
                head_table = "无来源分支数据"
                
            return f"### 目标分支分布\n{base_table}\n### 来源分支分布\n{head_table}"
        except Exception as e:
            print(f"分支分析生成失败: {str(e)}")
            return ""

    def _generate_lifetime_analysis(self) -> str:
        """生成PR生命周期分析部分"""
        try:
            lifetime_data = self.metrics.get("pr_lifetime_distribution", {})
            if not lifetime_data:
                return "无生命周期数据可分析"
                
            # 生成Markdown表格
            table_rows = []
            for period, count in lifetime_data.items():
                table_rows.append(f"| {period} | {count} |")
                
            table = "| 生命周期 | PR数量 |\n|----------|--------|\n" + "\n".join(table_rows)
            
            return table
        except Exception as e:
            print(f"生命周期分析生成失败: {str(e)}")
            return ""


class PRAnalyzer:
    """PR分析器主类，增强流程控制和结果输出"""

    def __init__(self, repo_full_name: str, config: PRAnalyzerConfig = None, github_token: Optional[str] = None):
        """
        初始化PR分析器

        :param repo_full_name: 仓库全名（如 "octocat/hello-world"）
        :param config: PR分析器配置对象
        :param github_token: GitHub访问令牌（可选，公开仓库可不需要）
        """
        self.repo_full_name = repo_full_name
        self.config = config or PRAnalyzerConfig()
        self.github_config = GitHubConfig(github_token, self.config)
        self.df = None
        self.metrics = None

    def run_analysis(self, save_reports: bool = True) -> Dict:
        """执行完整的PR分析流程"""
        try:
            print(f"开始分析流程 - 仓库: {self.repo_full_name}")
            
            # 1. 数据抓取
            print("1. 数据抓取阶段")
            fetcher = PRDataFetcher(self.github_config.client, self.repo_full_name, self.config)
            self.df = fetcher.fetch_pr_data()

            if len(self.df) == 0:
                print("未获取到任何PR数据，请检查网络连接和API配额")
                return {}

            # 2. 指标计算
            print("2. 指标计算阶段")
            calculator = PRMetricsCalculator(self.df, self.config)
            self.metrics = calculator.calculate_all_metrics()
            self.metrics['days_threshold'] = self.config.zombie_threshold_days  # 将阈值加入指标

            # 3. 生成可视化报告
            if save_reports:
                print("3. 生成可视化报告")
                visualizer = PRVisualizer(self.df, self.metrics, self.repo_full_name, self.config)
                viz_path = os.path.join(self.config.report_save_path, f"{self.repo_full_name.replace('/', '_')}_report.png")
                visualizer.generate_visualization(viz_path)

                # 4. 生成文字报告
                print("4. 生成文字报告")
                report_path = os.path.join(self.config.report_save_path, f"{self.repo_full_name.replace('/', '_')}_report.md")
                reporter = PRReportGenerator(self.metrics, self.repo_full_name, self.config)
                reporter.generate_text_report(report_path)
            
            print("分析流程完成")
            return self.metrics
            
        except Exception as e:
            print(f"分析流程失败: {str(e)}")
            return {}

def analyze_pr_repository(repo_full_name: str, days_threshold: int = 7, github_token: str = None, save_reports: bool = True) -> Dict:
    """
    分析GitHub仓库的PR数据（供main.py调用的入口函数）

    :param repo_full_name: 仓库全名（如 "owner/repo"）
    :param days_threshold: 僵尸PR的时间阈值（天）
    :param github_token: GitHub访问令牌
    :param save_reports: 是否保存报告文件
    :return: 分析结果字典
    """
    try:
        # 创建配置对象
        config = PRAnalyzerConfig(
            zombie_threshold_days=days_threshold,
            outlier_filter_days=30,
            report_save_path="reports"
        )

        # 创建分析器并执行分析
        analyzer = PRAnalyzer(repo_full_name, config, github_token)
        results = analyzer.run_analysis(save_reports=save_reports)

        return results

    except Exception as e:
        print(f"❌ PR分析失败: {str(e)}")
        return {}


if __name__ == "__main__":
    # 示例用法
    config = PRAnalyzerConfig(
        zombie_threshold_days=7,
        outlier_filter_days=30,
        report_save_path="analysis_reports"
    )

    analyzer = PRAnalyzer("octocat/Hello-World", config)
    results = analyzer.run_analysis()

    print(f"分析结果: {json.dumps(results, indent=2, ensure_ascii=False)}")
