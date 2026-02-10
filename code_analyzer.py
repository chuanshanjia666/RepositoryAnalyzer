import os
import json
import radon.complexity as cc
import radon.metrics as rm
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class AdvancedRadonAnalyzer:

    def __init__(self, repo_path, output_dir):
        self.repo_path = repo_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def get_python_files(self):
        """遍历所有Python文件"""
        py_files = []
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))
        return py_files

    def batch_analyze(self):
        """批量分析复杂度（修复mi_visit返回值问题）"""
        py_files = self.get_python_files()
        if not py_files:
            print("  未找到Python文件，跳过复杂度分析")
            return {}
        results = {
            "cyclomatic_complexity": [],
            "maintainability_index": [],
            "file_paths": []
        }
        for file_path in py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                cc_results = cc.cc_visit(content)
                avg_cc = sum(c.complexity for c in cc_results) / len(cc_results) if cc_results else 0.0
                mi = rm.mi_visit(content, multi=True)
                if isinstance(mi, (int, float)):
                    avg_mi = float(mi)
                elif isinstance(mi, list) and len(mi) > 0:
                    avg_mi = sum(mi) / len(mi)
                else:
                    avg_mi = 0.0
                results["cyclomatic_complexity"].append(avg_cc)
                results["maintainability_index"].append(avg_mi)
                results["file_paths"].append(file_path)
            except Exception as e:
                print(f" 分析 {file_path} 失败：{str(e)}")
                results["cyclomatic_complexity"].append(0.0)
                results["maintainability_index"].append(0.0)
                results["file_paths"].append(file_path)
                continue
        output_path = os.path.join(self.output_dir, "radon_complexity_analysis.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f" 复杂度分析完成（{len(py_files)}个文件，{len([x for x in results['cyclomatic_complexity'] if x > 0])}个有效文件）")
        return results

    def visualize_complexity(self, results):
        """可视化复杂度结果（过滤无效数据）"""
        if not results["file_paths"]:
            return
        valid_data = []
        for i in range(len(results["file_paths"])):
            if results["cyclomatic_complexity"][i] > 0 or results["maintainability_index"][i] > 0:
                valid_data.append({
                    "path": results["file_paths"][i],
                    "cc": results["cyclomatic_complexity"][i],
                    "mi": results["maintainability_index"][i]
                })
        if not valid_data:
            print("  无有效复杂度数据，跳过可视化")
            return
        simplified_paths = [
            os.path.join(os.path.basename(os.path.dirname(d["path"])), os.path.basename(d["path"]))[:20] + "..."
            for d in valid_data
        ]
        cc_values = [d["cc"] for d in valid_data]
        mi_values = [d["mi"] for d in valid_data]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        ax1.bar(range(len(simplified_paths)), cc_values, color="#ff7f7f")
        ax1.set_title("Python文件圈复杂度分布（有效文件）", fontsize=14)
        ax1.set_ylabel("平均圈复杂度", fontsize=12)
        ax1.set_xticks(range(len(simplified_paths)))
        ax1.set_xticklabels(simplified_paths, rotation=45, ha="right", fontsize=8)
        ax1.grid(axis="y", alpha=0.3)
        ax2.bar(range(len(simplified_paths)), mi_values, color="#7fbf7f")
        ax2.set_title("Python文件可维护性指数分布（有效文件）", fontsize=14)
        ax2.set_ylabel("平均可维护性指数", fontsize=12)
        ax2.set_xlabel("文件路径（简化）", fontsize=12)
        ax2.set_xticks(range(len(simplified_paths)))
        ax2.set_xticklabels(simplified_paths, rotation=45, ha="right", fontsize=8)
        ax2.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        output_path = os.path.join(self.output_dir, "radon_complexity_visualization.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f" 复杂度可视化图表已保存：{output_path}（{len(valid_data)}个有效文件）")
