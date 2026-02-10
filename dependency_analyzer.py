import json
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['font.sans-serif'] = ['Source Han Sans CN', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
REQUIRED_TOOLS = {
    "pipdeptree": "pip install pipdeptree>=2.5.0",
    "safety": "pip install safety>=2.3.5"
}

class DependencyAnalyzer:
    """项目依赖分析工具（支持Python/Maven/NPM，含漏洞检测和可视化）"""

    def __init__(self, repo_path: str, output_dir: str, timeout: int = 60):
        """
        初始化依赖分析器
        :param repo_path: 项目根路径
        :param output_dir: 可视化结果输出目录
        :param timeout: 子进程超时时间（秒，默认60）
        """
        self.repo_path = Path(repo_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.is_windows = platform.system() == "Windows"
        self.subprocess_timeout = timeout
        self._checked_tools = {}

    def _check_tool(self, tool_name: str) -> bool:
        """检查单个工具是否安装（缓存结果）"""
        if tool_name in self._checked_tools:
            return self._checked_tools[tool_name]
        try:
            cmd = ["python", "-m", tool_name, "--version"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
                check=True
            )
            self._checked_tools[tool_name] = True
            return True
        except Exception:
            self._checked_tools[tool_name] = False
            return False

    def _run_subprocess(self, cmd: List[str], desc: str) -> Optional[Dict[str, Any]]:
        """
        统一执行子进程命令（增强错误处理、超时控制、JSON解析）
        :param cmd: 待执行的命令列表
        :param desc: 命令描述（用于错误提示）
        :return: 解析后的JSON结果（失败返回None）
        """
        if self.is_windows and cmd[0] in ["mvn", "npm"]:
            cmd[0] += ".cmd"
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self.subprocess_timeout,
                check=True,
                encoding='utf-8',
                errors='replace'
            )
            if not result.stdout.strip():
                print(f"  {desc}返回空结果")
                return {}
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                lines = result.stdout.split('\n')
                cleaned_lines = []
                json_started = False
                for line in lines:
                    if (line.startswith(('+', '=', 'INFO', 'WARNING', 'ERROR', 'DEBUG', 'DEPREC'))
                        or not line.strip()):
                        continue
                    if line.strip().startswith('{') or line.strip().startswith('['):
                        json_started = True
                    if json_started:
                        cleaned_lines.append(line)
                cleaned_output = '\n'.join(cleaned_lines)
                if cleaned_output:
                    try:
                        return json.loads(cleaned_output)
                    except:
                        pass
                if "safety" in desc and ("No vulnerabilities found" in result.stdout or "DEPREC" in result.stdout):
                    return {"vulnerabilities": []}
                print(f"  {desc}返回非JSON格式（前200字符）：{result.stdout[:200]}")
                return None
        except subprocess.TimeoutExpired:
            print(f"  执行{desc}超时（{self.subprocess_timeout}秒），命令：{' '.join(cmd)}")
        except subprocess.CalledProcessError as e:
            if e.returncode == 64 and "safety" in cmd:
                print(f"  Safety检测返回非零状态码（64）：无漏洞依赖或配置问题")
                return {"vulnerabilities": []}
            print(f"  执行{desc}失败（返回码：{e.returncode}）：{e.stderr[:200]}")
        except FileNotFoundError as e:
            tool_name = None
            if "-m" in cmd:
                m_index = cmd.index("-m")
                if m_index + 1 < len(cmd):
                    tool_name = cmd[m_index + 1]
            tool_name = tool_name or cmd[0]
            install_cmd = REQUIRED_TOOLS.get(tool_name, f"pip install {tool_name}")
            print(f"  工具未安装：{tool_name}（执行：{install_cmd}）")
        except Exception as e:
            print(f"  执行{desc}出错：{str(e)[:200]}")
        return None

    def analyze_python_deps(self) -> Dict[str, Any]:
        """分析Python项目依赖（传递依赖+漏洞依赖）- 修复float不可迭代问题"""
        result = {
            "transitive_deps": [],
            "vulnerable_deps": [],
            "total_transitive": 0,
            "total_vulnerable": 0
        }
        req_file = self.repo_path / "requirements.txt"
        if not req_file.exists():
            print("  未找到requirements.txt，跳过Python依赖分析")
            return result
        if not self._check_tool("pipdeptree"):
            print("  pipdeptree未安装，跳过传递依赖分析")
        else:
            transitive_deps = self._run_subprocess(
                ["python", "-m", "pipdeptree", "--json"],
                "Python传递依赖解析（pipdeptree）"
            ) or []
            if not isinstance(transitive_deps, list):
                print(f"  pipdeptree返回非列表类型：{type(transitive_deps)}")
                transitive_deps = []
            parsed_deps = []
            for pkg in transitive_deps:
                if not isinstance(pkg, dict):
                    continue
                pkg_info = pkg.get("package", {})
                if not isinstance(pkg_info, dict):
                    continue
                pkg_name = pkg_info.get("key", "未知")
                pkg_version = pkg_info.get("version", "未知")
                parsed_deps.append({"name": pkg_name, "version": pkg_version})
            result["transitive_deps"] = parsed_deps
            result["total_transitive"] = len(parsed_deps)
        vulnerable_deps = self._check_vulnerable_deps()
        if not isinstance(vulnerable_deps, list):
            vulnerable_deps = []
            print("  漏洞依赖检测结果异常，已重置为空列表")
        result["vulnerable_deps"] = vulnerable_deps
        result["total_vulnerable"] = len(vulnerable_deps)
        return result

    def _check_vulnerable_deps(self) -> List[Any]:
        """检查有漏洞的依赖（适配safety实际输出结构，修复返回值类型）"""
        if not self._check_tool("safety"):
            print("  safety未安装，跳过漏洞依赖检测")
            return []
        result = self._run_subprocess(
            ["python", "-m", "safety", "check", "--json"],
            "Python漏洞依赖检测（safety）"
        )
        if result is None:
            return []
        if not isinstance(result, dict):
            print(f"  safety返回非字典类型：{type(result)}")
            return []
        vulnerable_deps = result.get("vulnerabilities", [])
        if not isinstance(vulnerable_deps, list):
            vulnerable_deps = []
            print(f"  safety返回的vulnerabilities非列表类型：{type(vulnerable_deps)}")
        if vulnerable_deps:
            print(f"  检测到 {len(vulnerable_deps)} 个有漏洞的依赖项")
        else:
            print(" 未检测到有漏洞的依赖")
        return vulnerable_deps

    def analyze_generic_deps(self) -> Dict[str, Any]:
        """分析通用项目依赖（Maven/NPM，增强兼容性）"""
        deps_info = {"type": "unknown", "dependencies": []}
        pom_path = self.repo_path / "pom.xml"
        if pom_path.exists():
            deps_info["type"] = "maven"
            deps_info["dependencies"] = self._analyze_maven_deps()
        package_json_path = self.repo_path / "package.json"
        if package_json_path.exists():
            deps_info["type"] = "npm"
            deps_info["dependencies"] = self._analyze_npm_deps()
        return deps_info

    def _analyze_maven_deps(self) -> List[str]:
        """解析Maven项目依赖（增强兼容性）"""
        try:
            cmd = ["mvn.cmd" if self.is_windows else "mvn", "-v"]
            subprocess.run(cmd, capture_output=True, timeout=10, check=True)
        except:
            print("  Maven未安装，跳过Maven依赖分析")
            return []
        cmd = [
            "mvn.cmd" if self.is_windows else "mvn",
            "dependency:list",
            "-DoutputType=json",
            "-DexcludeTransitive=false",
            "-f", str(self.repo_path / "pom.xml")
        ]
        result = self._run_subprocess(cmd, "Maven依赖分析")
        deps = []
        if result:
            deps_list = result.get("dependencies", [])
            if not isinstance(deps_list, list):
                deps_list = result.get("results", [])
            for dep in deps_list:
                if not isinstance(dep, dict):
                    continue
                dep_name = dep.get("artifactId", "未知")
                dep_version = dep.get("version", "未知")
                deps.append(f"{dep_name}:{dep_version}")
        return deps

    def _analyze_npm_deps(self) -> List[str]:
        """解析NPM项目依赖（增强递归解析和错误处理）"""
        try:
            cmd = ["npm.cmd" if self.is_windows else "npm", "-v"]
            subprocess.run(cmd, capture_output=True, timeout=10, check=True)
        except:
            print("  NPM未安装，跳过NPM依赖分析")
            return []
        cmd = ["npm.cmd" if self.is_windows else "npm", "list", "--json", "--prefix", str(self.repo_path)]
        result = self._run_subprocess(cmd, "NPM依赖分析")

        def _parse_npm_deps(deps: Any) -> List[str]:
            parsed = []
            if not isinstance(deps, dict):
                return parsed
            for name, info in deps.items():
                if not isinstance(info, dict):
                    continue
                version = info.get("version", "未知")
                parsed.append(f"{name}:{version}")
                if "dependencies" in info and isinstance(info["dependencies"], dict):
                    parsed.extend(_parse_npm_deps(info["dependencies"]))
            return parsed
        deps = []
        if result and isinstance(result, dict) and "dependencies" in result:
            deps = _parse_npm_deps(result["dependencies"])
        return deps

    def visualize_deps(self, deps_data: Dict[str, Any]) -> None:
        """可视化依赖分析结果（优化图表显示和错误处理）"""
        if not isinstance(deps_data, dict):
            print(" 依赖可视化失败：输入数据不是字典类型")
            return
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2)
            fig.suptitle("项目依赖分析报告", fontsize=16, fontweight='bold')
            self._plot_pie_chart(ax1, deps_data)
            self._plot_vulnerable_bar(ax2, deps_data.get("vulnerable_deps", []))
            output_path = self.output_dir / "dependency_analysis.png"
            plt.tight_layout()
            plt.savefig(
                output_path,
                dpi=300,
                bbox_inches="tight",
                facecolor='white',
                edgecolor='none'
            )
            plt.close(fig)
            print(f" 可视化报告已保存至：{output_path.absolute()}")
        except Exception as e:
            print(f" 依赖可视化失败：{e}")

    def _plot_pie_chart(self, ax, deps_data: Dict[str, Any]) -> None:
        """绘制传递依赖饼图（增强鲁棒性）"""
        total_transitive = deps_data.get("total_transitive", 0)
        total_vulnerable = deps_data.get("total_vulnerable", 0)
        if not isinstance(total_transitive, (int, float)):
            total_transitive = 0
        if not isinstance(total_vulnerable, (int, float)):
            total_vulnerable = 0
        safe_count = max(0, total_transitive - total_vulnerable)
        labels = []
        sizes = []
        colors = []
        if safe_count > 0:
            labels.append("安全依赖")
            sizes.append(safe_count)
            colors.append("#2E8B57")
        if total_vulnerable > 0:
            labels.append("漏洞依赖")
            sizes.append(total_vulnerable)
            colors.append("#DC143C")
        ax.set_title("传递依赖分布", fontsize=14, fontweight='bold', pad=20)
        if not sizes:
            ax.text(0.5, 0.5, "无依赖数据", ha="center", va="center", fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
            return
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors, autopct="%1.1f%%",
            startangle=90, textprops={"fontsize": 11},
            wedgeprops=dict(width=0.7, edgecolor='white', linewidth=2)
        )
        ax.set_aspect('equal')
        for text in texts:
            text.set_fontsize(11)
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")
            autotext.set_fontsize(10)

    def _plot_vulnerable_bar(self, ax, vulnerable_deps: List[Any]) -> None:
        """绘制漏洞依赖柱状图（修复float不可迭代问题）"""
        ax.set_title("有漏洞的依赖（按漏洞数量）", fontsize=14, fontweight='bold', pad=20)
        ax.set_ylabel("漏洞数量", fontsize=12)
        if not isinstance(vulnerable_deps, list):
            vulnerable_deps = []
            print("  漏洞依赖数据不是列表类型，已重置为空")
        vulnerable_count = len(vulnerable_deps)
        if vulnerable_count == 0:
            ax.text(0.5, 0.5, "未检测到有漏洞的依赖", ha="center", va="center", fontsize=12)
            ax.set_xticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            return
        vuln_counter = {}
        for vuln in vulnerable_deps:
            if not isinstance(vuln, dict):
                continue
            pkg_info = vuln.get("package", {})
            if not isinstance(pkg_info, dict):
                continue
            pkg_name = pkg_info.get("name", "未知")
            pkg_name = pkg_name[:12] + "..." if len(pkg_name) > 12 else pkg_name
            vuln_counter[pkg_name] = vuln_counter.get(pkg_name, 0) + 1
        if not vuln_counter:
            ax.text(0.5, 0.5, "无法解析漏洞依赖数据", ha="center", va="center", fontsize=12)
            ax.set_xticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            return
        names = list(vuln_counter.keys())
        counts = list(vuln_counter.values())
        if len(names) > 15:
            print(f"  漏洞依赖数量过多（{len(names)}个），仅显示前15个")
            names = names[:15]
            counts = counts[:15]
        bars = ax.bar(
            names, counts,
            color="#FF6347", edgecolor="#B22222",
            alpha=0.8, linewidth=1.5
        )
        ax.tick_params(axis='x', rotation=45, ha="right", labelsize=10)
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2., height + 0.05,
                str(count), ha='center', va='bottom',
                fontsize=10, fontweight='bold'
            )
        ax.add_patch(Rectangle((-0.5, 0), len(names), max(counts)*1.1,
                              facecolor='#F8F8F8', zorder=0))

    def run(self) -> Dict[str, Any]:
        """执行完整的依赖分析流程"""
        print(f" 开始分析项目依赖：{self.repo_path.absolute()}")
        deps_data = {"transitive_deps": [], "vulnerable_deps": [], "total_transitive": 0, "total_vulnerable": 0}
        python_files = [
            self.repo_path / "requirements.txt",
            self.repo_path / "pyproject.toml",
            self.repo_path / "setup.py"
        ]
        if any(f.exists() for f in python_files):
            print(" 检测到Python项目，开始解析依赖...")
            deps_data = self.analyze_python_deps()
        else:
            print(" 非Python项目，尝试解析通用依赖...")
            generic_deps = self.analyze_generic_deps()
            deps_data["transitive_deps"] = generic_deps["dependencies"]
            deps_data["total_transitive"] = len(generic_deps["dependencies"])
        self.visualize_deps(deps_data)
        print(f"\n 依赖分析完成：")
        print(f"   - 总传递依赖数：{deps_data['total_transitive']}")
        print(f"   - 漏洞依赖数：{deps_data['total_vulnerable']}")
        try:
            output_path = self.output_dir / "dependency_analysis_raw.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(deps_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  保存依赖分析原始数据失败：{e}")
        return deps_data

def main():
    """命令行入口函数（彻底移除global声明，修复语法错误）"""
    parser = argparse.ArgumentParser(
        description="项目依赖分析工具（支持Python/Maven/NPM）",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--repo-path",
        required=True,
        help="项目根目录路径"
    )
    parser.add_argument(
        "--output-dir",
        default="./dependency_report",
        help="可视化报告输出目录（默认：./dependency_report）"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="子进程超时时间（秒，默认：60）"
    )
    args = parser.parse_args()
    try:
        analyzer = DependencyAnalyzer(args.repo_path, args.output_dir, args.timeout)
        analyzer.run()
        print("\n 依赖分析工具执行完成！")
    except Exception as e:
        print(f"\n 分析失败：{str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
if __name__ == "__main__":
    main()
