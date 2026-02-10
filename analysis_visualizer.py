import os
import re
import matplotlib.pyplot as plt
from collections import Counter
plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'Arial Unicode MS', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def parse_pylint_report(file_path):
    if not os.path.exists(file_path):
        return None
    counts = Counter()
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r': ([CRWE])\d{4}:', line)
            if match:
                counts[match.group(1)] += 1
    return counts

def parse_radon_report(file_path):
    if not os.path.exists(file_path):
        return None
    grades = Counter()
    file_complexity = {}
    current_file = None
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('/'):
                current_file = os.path.basename(line)
            else:
                match = re.search(r' - ([A-F]) \((\d+)\)', line)
                if match:
                    grade = match.group(1)
                    score = int(match.group(2))
                    grades[grade] += 1
                    if current_file:
                        file_complexity[current_file] = max(file_complexity.get(current_file, 0), score)
    return grades, file_complexity

def parse_bandit_report(file_path):
    if not os.path.exists(file_path):
        return None
    severities = Counter()
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r'Severity: (\w+)', line)
            if match:
                severities[match.group(1)] += 1
    return severities

def draw_pylint_pie(counts, output_path):
    if not counts: return
    labels_map = {'C': '规范 (Convention)', 'R': '重构 (Refactor)', 'W': '警告 (Warning)', 'E': '错误 (Error)'}
    labels = [labels_map.get(k, k) for k in counts.keys()]
    values = counts.values()
    plt.figure(figsize=(8, 8))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
    plt.title('Pylint 代码质量问题分布')
    plt.savefig(output_path)
    plt.close()

def draw_radon_bar(grades, output_path):
    if not grades: return
    all_grades = ['A', 'B', 'C', 'D', 'E', 'F']
    values = [grades.get(g, 0) for g in all_grades]
    plt.figure(figsize=(10, 6))
    plt.bar(all_grades, values, color='skyblue')
    plt.title('Radon 代码圈复杂度等级分布 (A最简 -> F最复杂)')
    plt.xlabel('复杂度等级')
    plt.ylabel('函数/方法数量')
    plt.savefig(output_path)
    plt.close()

def draw_bandit_pie(severities, output_path):
    if not severities: return
    plt.figure(figsize=(8, 8))
    plt.pie(severities.values(), labels=severities.keys(), autopct='%1.1f%%', colors=['#ff6666', '#ffcc99', '#99ff99'])
    plt.title('Bandit 安全风险等级分布')
    plt.savefig(output_path)
    plt.close()

def run_visualizations(report_dir, prefix="comtool_"):
    pylint_counts = parse_pylint_report(os.path.join(report_dir, f"{prefix}pylint_report.txt"))
    draw_pylint_pie(pylint_counts, os.path.join(report_dir, f"{prefix}viz_pylint.png"))
    radon_data = parse_radon_report(os.path.join(report_dir, f"{prefix}radon_complexity.txt"))
    if radon_data:
        grades, file_comp = radon_data
        draw_radon_bar(grades, os.path.join(report_dir, f"{prefix}viz_radon.png"))
    bandit_severities = parse_bandit_report(os.path.join(report_dir, f"{prefix}bandit_report.txt"))
    draw_bandit_pie(bandit_severities, os.path.join(report_dir, f"{prefix}viz_bandit.png"))
if __name__ == "__main__":
    run_visualizations("reports")
    print("分析报告可视化已完成")
