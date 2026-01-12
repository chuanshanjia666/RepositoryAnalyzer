import os
import matplotlib.pyplot as plt
from datetime import datetime
from collections import Counter

plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'Arial Unicode MS', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def get_save_path(filename, output_dir, prefix):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return os.path.join(output_dir, f"{prefix}{filename}")

def draw_author_stats(commits, output_dir="stats", prefix=""):
    authors = [c['author'] for c in commits]
    author_counts = Counter(authors).most_common(10)
    plt.figure(figsize=(10, 6))
    names, counts = zip(*author_counts) if author_counts else ([], [])
    plt.barh(names, counts, color='skyblue')
    plt.title('前 10 名作者提交数统计')
    plt.xlabel('提交次数')
    plt.tight_layout()
    path = get_save_path('stats_authors.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_monthly_activity(commits, output_dir="stats", prefix=""):
    months = [c['date'][:7] for c in commits]
    month_counts = Counter(months)
    sorted_months = sorted(month_counts.items())
    plt.figure(figsize=(12, 6))
    if sorted_months:
        m_labels, m_values = zip(*sorted_months)
        plt.plot(m_labels, m_values, marker='o', linestyle='-', color='green')
        plt.xticks(rotation=45)
    plt.title('每月提交频率趋势')
    plt.ylabel('提交次数')
    plt.tight_layout()
    path = get_save_path('stats_monthly.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_keyword_distribution(commits, output_dir="stats", prefix=""):
    keywords = {'新增 (add)': 0, '更新 (update)': 0, '修复 (fix)': 0, '其他': 0}
    for c in commits:
        msg = c['message'].lower()
        if 'add' in msg:
            keywords['新增 (add)'] += 1
        elif 'update' in msg:
            keywords['更新 (update)'] += 1
        elif 'fix' in msg:
            keywords['修复 (fix)'] += 1
        else:
            keywords['其他'] += 1
    plt.figure(figsize=(8, 8))
    plt.pie(keywords.values(), labels=keywords.keys(), autopct='%1.1f%%', 
            colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
    plt.title('提交信息关键词分布')
    path = get_save_path('stats_keywords.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_day_of_week_activity(commits, output_dir="stats", prefix=""):
    days = [datetime.strptime(c['date'], '%Y-%m-%d %H:%M').weekday() for c in commits]
    day_counts = Counter(days)
    day_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    counts_by_day = [day_counts.get(i, 0) for i in range(7)]
    plt.figure(figsize=(10, 5))
    plt.bar(day_labels, counts_by_day, color='teal')
    plt.title('每周提交演变分布')
    plt.ylabel('提交次数')
    path = get_save_path('stats_dow.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_hourly_activity(commits, output_dir="stats", prefix=""):
    hours = [datetime.strptime(c['date'], '%Y-%m-%d %H:%M').hour for c in commits]
    hour_counts = Counter(hours)
    hour_labels = [f"{i:02d}h" for i in range(24)]
    counts_by_hour = [hour_counts.get(i, 0) for i in range(24)]
    plt.figure(figsize=(12, 5))
    plt.plot(hour_labels, counts_by_hour, marker='s', color='orange')
    plt.fill_between(hour_labels, counts_by_hour, alpha=0.2, color='orange')
    plt.title('全天时段提交活跃度')
    plt.xlabel('小时')
    plt.ylabel('提交次数')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    path = get_save_path('stats_hourly.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def analyze_message_metrics(commits, output_dir="stats", prefix=""):
    lengths = [len(c['message']) for c in commits]
    plt.figure(figsize=(10, 6))
    plt.hist(lengths, bins=20, color='plum', edgecolor='black')
    plt.title('提交信息长度分布情况')
    plt.xlabel('长度 (字符数)')
    plt.ylabel('频率')
    path = get_save_path('stats_msg_lengths.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def analyze_cumulative_growth(commits, output_dir="stats", prefix=""):
    sorted_commits = sorted(commits, key=lambda x: x['date'])
    dates = [datetime.strptime(c['date'], '%Y-%m-%d %H:%M') for c in sorted_commits]
    cumulative_counts = list(range(1, len(dates) + 1))
    plt.figure(figsize=(10, 6))
    plt.plot(dates, cumulative_counts, color='crimson', linewidth=2)
    plt.fill_between(dates, cumulative_counts, color='crimson', alpha=0.1)
    plt.title('项目提交累计增长曲线')
    plt.xlabel('日期')
    plt.ylabel('总提交数')
    plt.grid(True, which='both', linestyle='--', alpha=0.5)
    path = get_save_path('stats_growth.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def analyze_hotspots(repo, limit=100, output_dir="stats", prefix=""):
    dir_counter = Counter()
    for commit in repo.iter_commits('--all', max_count=limit):
        files = commit.stats.files.keys()
        for f in files:
            directory = f.split('/')[0] if '/' in f else '根目录 (root)'
            dir_counter[directory] += 1
    top_dirs = dir_counter.most_common(10)
    if not top_dirs:
        return
    plt.figure(figsize=(10, 6))
    dirs, counts = zip(*top_dirs)
    plt.bar(dirs, counts, color='gold')
    plt.title('最常被修改的前 10 个目录')
    plt.xticks(rotation=45)
    plt.ylabel('修改频率')
    plt.tight_layout()
    path = get_save_path('stats_hotspots.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_merge_activities(commits, output_dir="stats", prefix=""):
    merge_commits = [c for c in commits if len(c['parents']) > 1]
    months = [c['date'][:7] for c in merge_commits]
    merge_month_counts = Counter(months)
    sorted_months = sorted(merge_month_counts.items())
    plt.figure(figsize=(12, 6))
    if sorted_months:
        m_labels, m_values = zip(*sorted_months)
        plt.bar(m_labels, m_values, color='mediumpurple')
        plt.xticks(rotation=45)
    plt.title('每月合并 (PR 完成) 活动统计')
    plt.ylabel('合并次数')
    plt.tight_layout()
    path = get_save_path('stats_merges.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_merge_ratio(commits, output_dir="stats", prefix=""):
    merge_commits = [c for c in commits if len(c['parents']) > 1]
    total = len(commits)
    merges = len(merge_commits)
    plt.figure(figsize=(8, 8))
    plt.pie([merges, total-merges], labels=['合并提交 (Merge)', '普通提交 (Normal)'], 
            autopct='%1.1f%%', colors=['#6c5ce7', '#a29bfe'])
    plt.title('合并提交与普通提交占比')
    path = get_save_path('stats_merge_ratio.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_file_type_distribution(repo, limit=100, output_dir="stats", prefix=""):
    ext_counter = Counter()
    for commit in repo.iter_commits('--all', max_count=limit):
        for f in commit.stats.files.keys():
            ext = os.path.splitext(f)[1].lower()
            if not ext: ext = '无后缀'
            ext_counter[ext] += 1
    top_exts = ext_counter.most_common(10)
    if not top_exts: return
    plt.figure(figsize=(10, 6))
    exts, counts = zip(*top_exts)
    plt.bar(exts, counts, color='lightcoral')
    plt.title('最常修改的文件类型 (前 10)')
    plt.ylabel('修改次数')
    plt.tight_layout()
    path = get_save_path('stats_file_types.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_weekly_velocity(commits, output_dir="stats", prefix=""):
    weeks = {}
    for c in commits:
        dt = datetime.strptime(c['date'], '%Y-%m-%d %H:%M')
        year_week = dt.strftime('%Y-W%W')
        weeks[year_week] = weeks.get(year_week, 0) + 1
    sorted_weeks = sorted(weeks.items())
    plt.figure(figsize=(15, 6))
    if sorted_weeks:
        w_labels, w_values = zip(*sorted_weeks)
        plt.plot(w_labels, w_values, color='dodgerblue', marker='.')
        plt.xticks(rotation=90, fontsize=8)
    plt.title('每周提交速度趋势')
    plt.ylabel('提交次数')
    plt.tight_layout()
    path = get_save_path('stats_weekly.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_loc_evolution(repo, limit=200, output_dir="stats", prefix=""):
    dates = []
    cumulative_loc = 0
    loc_history = []
    commits = list(repo.iter_commits('--all', max_count=limit))
    commits.reverse()
    for commit in commits:
        stats = commit.stats.total
        net_change = stats['insertions'] - stats['deletions']
        cumulative_loc += net_change
        dt = datetime.fromtimestamp(commit.authored_date)
        dates.append(dt)
        loc_history.append(cumulative_loc)
    plt.figure(figsize=(12, 6))
    plt.plot(dates, loc_history, color='forestgreen', linewidth=1.5)
    plt.fill_between(dates, loc_history, color='forestgreen', alpha=0.1)
    plt.title('代码库净行数演变趋势 (LOC)')
    plt.xlabel('日期')
    plt.ylabel('累计行数 (净值)')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    path = get_save_path('stats_loc.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def draw_release_timeline(repo, output_dir="stats", prefix=""):
    tags = sorted(repo.tags, key=lambda t: t.commit.authored_date)
    if not tags:
        print("未发现 Release 标签，跳过发布统计。")
        return
    tag_names = [t.name for t in tags]
    tag_dates = [datetime.fromtimestamp(t.commit.authored_date) for t in tags]
    plt.figure(figsize=(12, 6))
    plt.scatter(tag_dates, [1] * len(tag_dates), color='red', s=100, zorder=3)
    for i, (date, name) in enumerate(zip(tag_dates, tag_names)):
        plt.vlines(date, 0, 1, colors='grey', linestyles='--', alpha=0.3)
        plt.text(date, 1.05 if i % 2 == 0 else 0.9, name, 
                 rotation=45, ha='right', fontsize=9, color='darkred')
    plt.title('项目 Release (Tag) 发布时间轴')
    plt.yticks([])
    plt.xlabel('发布年份/月份')
    plt.ylim(0.5, 1.5)
    plt.grid(axis='x', linestyle=':', alpha=0.5)
    plt.tight_layout()
    path = get_save_path('stats_releases.png', output_dir, prefix)
    plt.savefig(path)
    plt.close()
    print(f"已生成统计图: {path}")

def run_all_analysis(repo, commits, output_dir="stats", prefix=""):
    draw_author_stats(commits, output_dir, prefix)
    draw_monthly_activity(commits, output_dir, prefix)
    draw_keyword_distribution(commits, output_dir, prefix)
    draw_day_of_week_activity(commits, output_dir, prefix)
    draw_hourly_activity(commits, output_dir, prefix)
    analyze_message_metrics(commits, output_dir, prefix)
    analyze_cumulative_growth(commits, output_dir, prefix)
    analyze_hotspots(repo, 200, output_dir, prefix)
    draw_merge_activities(commits, output_dir, prefix)
    draw_merge_ratio(commits, output_dir, prefix)
    draw_file_type_distribution(repo, 200, output_dir, prefix)
    draw_weekly_velocity(commits, output_dir, prefix)
    draw_loc_evolution(repo, 300, output_dir, prefix)
    draw_release_timeline(repo, output_dir, prefix)
