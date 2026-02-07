import json
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# 全局配置抽离 - 统一维护可视化样式
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial Unicode MS"]  # 兼容不同系统中文
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题
plt.rcParams["figure.figsize"] = (14, 7)   # 优化图表尺寸
plt.rcParams["figure.dpi"] = 100           # 默认DPI
plt.rcParams["savefig.dpi"] = 300          # 保存图片DPI

# 必要工具映射（工具名: 安装命令）
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
        
        # 系统兼容性处理
        self.is_windows = platform.system() == "Windows"
        
        # 超时配置改为实例变量（彻底移除全局变量）
        self.subprocess_timeout = timeout
        
        # 前置检查：跳过工具检查，改为懒加载+优雅降级
        self._checked_tools = {}

    def _check_tool(self, tool_name: str) -> bool:
        """检查单个工具是否安装（缓存结果）"""
        if tool_name in self._checked_tools:
            return self._checked_tools[tool_name]
        
        try:
            # 执行版本检查，静默运行
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
        # Windows系统兼容性处理
        if self.is_windows and cmd[0] in ["mvn", "npm"]:
            cmd[0] += ".cmd"
        
        try:
            # 执行子进程，超时控制（引用实例变量）
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self.subprocess_timeout,
                check=True,
                # 解决Windows编码问题
                encoding='utf-8',
                errors='replace'
            )
            
            # 空输出处理
            if not result.stdout.strip():
                print(f"⚠️  {desc}返回空结果")
                return {}
            
            # 解析JSON结果
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # 尝试清理非JSON内容
                cleaned_output = '\n'.join(
                    line for line in result.stdout.split('\n') 
                    if not line.startswith(('INFO', 'WARNING', 'ERROR', 'DEBUG'))
                )
                if cleaned_output:
                    try:
                        return json.loads(cleaned_output)
                    except:
                        pass
                print(f"⚠️  {desc}返回非JSON格式（前200字符）：{result.stdout[:200]}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"⚠️  执行{desc}超时（{self.subprocess_timeout}秒），命令：{' '.join(cmd)}")
        except subprocess.CalledProcessError as e:
            # 区分不同错误码处理
            if e.returncode == 64 and "safety" in cmd:
                print(f"⚠️  Safety检测返回非零状态码（64）：无漏洞依赖或配置问题")
                return {"vulnerabilities": []}
            print(f"⚠️  执行{desc}失败（返回码：{e.returncode}）：{e.stderr[:200]}")
        except FileNotFoundError as e:
            # 工具未安装提示
            tool_name = None
            if "-m" in cmd:
                m_index = cmd.index("-m")
                if m_index + 1 < len(cmd):
                    tool_name = cmd[m_index + 1]
            tool_name = tool_name or cmd[0]
            
            install_cmd = REQUIRED_TOOLS.get(tool_name, f"pip install {tool_name}")
            print(f"⚠️  工具未安装：{tool_name}（执行：{install_cmd}）")
        except Exception as e:
            print(f"⚠️  执行{desc}出错：{str(e)[:200]}")
        
        return None

    def analyze_python_deps(self) -> Dict[str, Any]:
        """分析Python项目依赖（传递依赖+漏洞依赖）- 修复float不可迭代问题"""
        # 初始化默认返回值，确保类型安全
        result = {
            "transitive_deps": [],
            "vulnerable_deps": [],
            "total_transitive": 0,
            "total_vulnerable": 0
        }
        
        # 1. 检查requirements.txt是否存在
        req_file = self.repo_path / "requirements.txt"
        if not req_file.exists():
            print("⚠️  未找到requirements.txt，跳过Python依赖分析")
            return result
        
        # 2. 解析传递依赖（pipdeptree）
        if not self._check_tool("pipdeptree"):
            print("⚠️  pipdeptree未安装，跳过传递依赖分析")
        else:
            transitive_deps = self._run_subprocess(
                ["python", "-m", "pipdeptree", "--json"],
                "Python传递依赖解析（pipdeptree）"
            ) or []
            
            # 关键修复：确保结果是可迭代的列表
            if not isinstance(transitive_deps, list):
                print(f"⚠️  pipdeptree返回非列表类型：{type(transitive_deps)}")
                transitive_deps = []
            
            # 结构化解析依赖（增加类型检查）
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
        
        # 3. 检测漏洞依赖（safety）
        vulnerable_deps = self._check_vulnerable_deps()
        # 确保漏洞依赖是列表类型
        if not isinstance(vulnerable_deps, list):
            vulnerable_deps = []
            print("⚠️  漏洞依赖检测结果异常，已重置为空列表")
        
        result["vulnerable_deps"] = vulnerable_deps
        result["total_vulnerable"] = len(vulnerable_deps)
        
        return result

    def _check_vulnerable_deps(self) -> List[Any]:
        """检查有漏洞的依赖（适配safety实际输出结构，修复返回值类型）"""
        if not self._check_tool("safety"):
            print("⚠️  safety未安装，跳过漏洞依赖检测")
            return []
        
        result = self._run_subprocess(
            ["python", "-m", "safety", "check", "--json"],
            "Python漏洞依赖检测（safety）"
        )
        
        # 多重类型检查，确保返回列表
        if result is None:
            return []
        
        if not isinstance(result, dict):
            print(f"⚠️  safety返回非字典类型：{type(result)}")
            return []
        
        # 兼容不同版本的safety输出
        vulnerable_deps = result.get("vulnerabilities", [])
        if not isinstance(vulnerable_deps, list):
            vulnerable_deps = []
            print(f"⚠️  safety返回的vulnerabilities非列表类型：{type(vulnerable_deps)}")
        
        if vulnerable_deps:
            print(f"⚠️  检测到 {len(vulnerable_deps)} 个有漏洞的依赖项")
        else:
            print("✅ 未检测到有漏洞的依赖")
        
        return vulnerable_deps

    def analyze_generic_deps(self) -> Dict[str, Any]:
        """分析通用项目依赖（Maven/NPM，增强兼容性）"""
        deps_info = {"type": "unknown", "dependencies": []}
        
        # 检测Maven项目
        pom_path = self.repo_path / "pom.xml"
        if pom_path.exists():
            deps_info["type"] = "maven"
            deps_info["dependencies"] = self._analyze_maven_deps()
        
        # 检测NPM项目
        package_json_path = self.repo_path / "package.json"
        if package_json_path.exists():
            deps_info["type"] = "npm"
            deps_info["dependencies"] = self._analyze_npm_deps()
        
        return deps_info

    def _analyze_maven_deps(self) -> List[str]:
        """解析Maven项目依赖（增强兼容性）"""
        # 检查mvn是否安装
        try:
            cmd = ["mvn.cmd" if self.is_windows else "mvn", "-v"]
            subprocess.run(cmd, capture_output=True, timeout=10, check=True)
        except:
            print("⚠️  Maven未安装，跳过Maven依赖分析")
            return []
        
        cmd = [
            "mvn.cmd" if self.is_windows else "mvn", 
            "dependency:list",
            "-DoutputType=json",
            "-DexcludeTransitive=false",
            "-f", str(self.repo_path / "pom.xml")
        ]
        result = self._run_subprocess(cmd, "Maven依赖分析")
        
        # 简化解析（兼容不同Maven版本输出）
        deps = []
        if result:
            # 兼容不同的输出结构
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
        # 检查npm是否安装
        try:
            cmd = ["npm.cmd" if self.is_windows else "npm", "-v"]
            subprocess.run(cmd, capture_output=True, timeout=10, check=True)
        except:
            print("⚠️  NPM未安装，跳过NPM依赖分析")
            return []
        
        cmd = ["npm.cmd" if self.is_windows else "npm", "list", "--json", "--prefix", str(self.repo_path)]
        result = self._run_subprocess(cmd, "NPM依赖分析")
        
        # 递归解析npm依赖树（增加类型检查）
        def _parse_npm_deps(deps: Any) -> List[str]:
            parsed = []
            if not isinstance(deps, dict):
                return parsed
                
            for name, info in deps.items():
                if not isinstance(info, dict):
                    continue
                version = info.get("version", "未知")
                parsed.append(f"{name}:{version}")
                # 递归解析子依赖
                if "dependencies" in info and isinstance(info["dependencies"], dict):
                    parsed.extend(_parse_npm_deps(info["dependencies"]))
            return parsed
        
        deps = []
        if result and isinstance(result, dict) and "dependencies" in result:
            deps = _parse_npm_deps(result["dependencies"])
        
        return deps

    def visualize_deps(self, deps_data: Dict[str, Any]) -> None:
        """可视化依赖分析结果（优化图表显示和错误处理）"""
        # 确保输入数据类型安全
        if not isinstance(deps_data, dict):
            print("❌ 依赖可视化失败：输入数据不是字典类型")
            return
        
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2)
            fig.suptitle("项目依赖分析报告", fontsize=16, fontweight='bold')
            
            # 绘制传递依赖饼图
            self._plot_pie_chart(ax1, deps_data)
            
            # 绘制漏洞依赖柱状图
            self._plot_vulnerable_bar(ax2, deps_data.get("vulnerable_deps", []))
            
            # 保存可视化结果
            output_path = self.output_dir / "dependency_analysis.png"
            plt.tight_layout()
            plt.savefig(
                output_path, 
                dpi=300, 
                bbox_inches="tight",
                facecolor='white',
                edgecolor='none'
            )
            plt.close(fig)  # 释放内存
            print(f"✅ 可视化报告已保存至：{output_path.absolute()}")
            
        except Exception as e:
            print(f"❌ 依赖可视化失败：{e}")

    def _plot_pie_chart(self, ax, deps_data: Dict[str, Any]) -> None:
        """绘制传递依赖饼图（增强鲁棒性）"""
        # 提取数据并确保类型安全
        total_transitive = deps_data.get("total_transitive", 0)
        total_vulnerable = deps_data.get("total_vulnerable", 0)
        
        # 数值校验
        if not isinstance(total_transitive, (int, float)):
            total_transitive = 0
        if not isinstance(total_vulnerable, (int, float)):
            total_vulnerable = 0
        
        safe_count = max(0, total_transitive - total_vulnerable)
        
        # 过滤数量为0的项，避免图表异常
        labels = []
        sizes = []
        colors = []
        if safe_count > 0:
            labels.append("安全依赖")
            sizes.append(safe_count)
            colors.append("#2E8B57")  # 深绿
        if total_vulnerable > 0:
            labels.append("漏洞依赖")
            sizes.append(total_vulnerable)
            colors.append("#DC143C")  # 深红
        
        ax.set_title("传递依赖分布", fontsize=14, fontweight='bold', pad=20)
        
        if not sizes:
            ax.text(0.5, 0.5, "无依赖数据", ha="center", va="center", fontsize=12)
            # 隐藏坐标轴
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
            return
        
        # 绘制饼图（添加百分比标签）
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors, autopct="%1.1f%%",
            startangle=90, textprops={"fontsize": 11},
            wedgeprops=dict(width=0.7, edgecolor='white', linewidth=2)  # 环形图更美观
        )
        ax.set_aspect('equal')
        
        # 美化标签
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
        
        # 确保输入是列表
        if not isinstance(vulnerable_deps, list):
            vulnerable_deps = []
            print("⚠️  漏洞依赖数据不是列表类型，已重置为空")
        
        vulnerable_count = len(vulnerable_deps)
        if vulnerable_count == 0:
            ax.text(0.5, 0.5, "未检测到有漏洞的依赖", ha="center", va="center", fontsize=12)
            # 美化空图表
            ax.set_xticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            return
        
        # 统计每个依赖的漏洞数量（增加类型检查）
        vuln_counter = {}
        for vuln in vulnerable_deps:
            if not isinstance(vuln, dict):
                continue
                
            pkg_info = vuln.get("package", {})
            if not isinstance(pkg_info, dict):
                continue
                
            pkg_name = pkg_info.get("name", "未知")
            # 截断超长名称，避免图表显示异常
            pkg_name = pkg_name[:12] + "..." if len(pkg_name) > 12 else pkg_name
            vuln_counter[pkg_name] = vuln_counter.get(pkg_name, 0) + 1
        
        # 处理空统计结果
        if not vuln_counter:
            ax.text(0.5, 0.5, "无法解析漏洞依赖数据", ha="center", va="center", fontsize=12)
            ax.set_xticks([])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            return
        
        # 绘制柱状图
        names = list(vuln_counter.keys())
        counts = list(vuln_counter.values())
        
        # 限制显示数量，避免图表拥挤
        if len(names) > 15:
            print(f"⚠️  漏洞依赖数量过多（{len(names)}个），仅显示前15个")
            names = names[:15]
            counts = counts[:15]
        
        bars = ax.bar(
            names, counts, 
            color="#FF6347", edgecolor="#B22222", 
            alpha=0.8, linewidth=1.5
        )
        
        # 美化柱状图
        ax.tick_params(axis='x', rotation=45, ha="right", labelsize=10)
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # 添加数值标签
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2., height + 0.05,
                str(count), ha='center', va='bottom', 
                fontsize=10, fontweight='bold'
            )
        
        # 添加背景色
        ax.add_patch(Rectangle((-0.5, 0), len(names), max(counts)*1.1, 
                              facecolor='#F8F8F8', zorder=0))

    def run(self) -> Dict[str, Any]:
        """执行完整的依赖分析流程"""
        print(f"📊 开始分析项目依赖：{self.repo_path.absolute()}")
        
        # 1. 检测项目类型并分析依赖
        deps_data = {"transitive_deps": [], "vulnerable_deps": [], "total_transitive": 0, "total_vulnerable": 0}
        
        # 检测Python项目特征文件
        python_files = [
            self.repo_path / "requirements.txt",
            self.repo_path / "pyproject.toml",
            self.repo_path / "setup.py"
        ]
        
        if any(f.exists() for f in python_files):
            print("🔍 检测到Python项目，开始解析依赖...")
            deps_data = self.analyze_python_deps()
        else:
            print("🔍 非Python项目，尝试解析通用依赖...")
            generic_deps = self.analyze_generic_deps()
            deps_data["transitive_deps"] = generic_deps["dependencies"]
            deps_data["total_transitive"] = len(generic_deps["dependencies"])
        
        # 2. 生成可视化报告
        self.visualize_deps(deps_data)
        
        # 3. 返回分析结果
        print(f"\n📈 依赖分析完成：")
        print(f"   - 总传递依赖数：{deps_data['total_transitive']}")
        print(f"   - 漏洞依赖数：{deps_data['total_vulnerable']}")
        
        # 保存原始数据
        try:
            output_path = self.output_dir / "dependency_analysis_raw.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(deps_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  保存依赖分析原始数据失败：{e}")
            
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
        default=60,  # 直接使用字面量默认值，避免全局变量引用
        help="子进程超时时间（秒，默认：60）"
    )
    
    args = parser.parse_args()
    
    # 直接传递超时参数给类实例，无需修改全局变量
    try:
        analyzer = DependencyAnalyzer(args.repo_path, args.output_dir, args.timeout)
        analyzer.run()
        print("\n✅ 依赖分析工具执行完成！")
    except Exception as e:
        print(f"\n❌ 分析失败：{str(e)}")
        # 打印详细异常栈
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()