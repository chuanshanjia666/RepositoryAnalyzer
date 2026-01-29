import os
import json
import subprocess
from pathlib import Path
import matplotlib.pyplot as plt

# 解决中文显示
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

class DependencyAnalyzer:
    def __init__(self, repo_path, output_dir):
        self.repo_path = repo_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def analyze_python_deps(self):
        """分析Python依赖"""
        deps = {
            "direct_deps": [],
            "transitive_deps": [],
            "vulnerable_deps": []
        }

        # 1. 解析requirements.txt
        req_file = Path(self.repo_path) / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, "r", encoding="utf-8") as f:
                    deps["direct_deps"] = [
                        line.strip() for line in f 
                        if line.strip() and not line.startswith("#")
                    ]
                print(f"✅ 解析到 {len(deps['direct_deps'])} 个直接依赖（requirements.txt）")
            except Exception as e:
                print(f"⚠️  解析requirements.txt失败：{str(e)}")

        # 2. pipdeptree分析传递依赖
        try:
            result = subprocess.run(
                ["python", "-m", "pipdeptree", "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            if result.returncode == 0:
                deps["transitive_deps"] = json.loads(result.stdout)
                print(f"✅ 解析到 {len(deps['transitive_deps'])} 个传递依赖")
        except Exception as e:
            print(f"⚠️  分析传递依赖失败：{str(e)}（需安装：python -m pip install pipdeptree）")

        # 3. safety检查漏洞依赖
        try:
            result = subprocess.run(
                ["python", "-m", "safety", "check", "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            if result.returncode == 0 and result.stdout:
                deps["vulnerable_deps"] = json.loads(result.stdout)
                print(f"⚠️  检测到 {len(deps['vulnerable_deps'])} 个有漏洞的依赖")
        except Exception as e:
            print(f"⚠️  检查漏洞依赖失败：{str(e)}（需安装：python -m pip install safety）")

        # 保存结果
        output_path = os.path.join(self.output_dir, "python_dependency_analysis.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(deps, f, ensure_ascii=False, indent=4)
        
        return deps

    def analyze_generic_deps(self):
        """通用依赖分析（Java/JS）"""
        # Maven
        if (Path(self.repo_path) / "pom.xml").exists():
            print("✅ 检测到Maven项目（pom.xml）")
        # NPM
        if (Path(self.repo_path) / "package.json").exists():
            print("✅ 检测到NPM项目（package.json）")

    def visualize_deps(self, deps):
        """可视化依赖结果"""
        direct_count = len(deps["direct_deps"])
        transitive_count = len(deps["transitive_deps"]) if isinstance(deps["transitive_deps"], list) else 0
        vulnerable_count = len(deps["vulnerable_deps"])

        # 绘制图表
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # 饼图：依赖类型分布
        labels = ["直接依赖", "传递依赖", "有漏洞依赖"]
        sizes = [direct_count, transitive_count, vulnerable_count]
        colors = ["#66b3ff", "#99ff99", "#ff9999"]
        ax1.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
        ax1.set_title("Python依赖类型分布", fontsize=14)

        # 柱状图：漏洞依赖
        if vulnerable_count > 0:
            vuln_names = [v.get("package", {}).get("name", "未知")[:10] + "..." for v in deps["vulnerable_deps"]]
            vuln_counts = [1] * vulnerable_count
            ax2.bar(vuln_names, vuln_counts, color="#ff6666")
            ax2.set_title("有漏洞的依赖", fontsize=14)
            ax2.set_ylabel("漏洞数量", fontsize=12)
            ax2.set_xticklabels(vuln_names, rotation=45, ha="right")
        else:
            ax2.text(0.5, 0.5, "未检测到有漏洞的依赖", ha="center", va="center", fontsize=12)
            ax2.set_title("有漏洞的依赖", fontsize=14)

        # 保存
        plt.tight_layout()
        output_path = os.path.join(self.output_dir, "dependency_visualization.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        
        print(f"✅ 依赖可视化图表已保存：{output_path}")