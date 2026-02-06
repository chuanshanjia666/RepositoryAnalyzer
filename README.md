# RepositoryAnalyzer - 代码仓库分析工具

RepositoryAnalyzer 是一个功能强大的代码仓库分析工具，专门用于深度分析 Git 仓库的结构、代码质量、依赖关系和安全性。它提供了丰富的可视化报告，帮助开发者全面了解项目的技术状况。

## ✨ 主要特性

### 🔍 全面的代码分析
- **代码复杂度分析**：使用 Radon 工具分析 Python 代码的圈复杂度、代码行数等指标
- **依赖关系分析**：自动识别和分析项目的依赖包及版本信息
- **安全漏洞扫描**：集成 Bandit 工具进行代码安全漏洞检测
- **Git 历史分析**：深度分析提交历史、分支结构和开发活动

### 📊 丰富的可视化报告
- **交互式 Git 树状图**：使用 GitGraph 可视化展示分支和提交历史
- **代码复杂度热力图**：直观展示各模块的复杂度分布
- **依赖关系图**：图形化展示项目依赖结构
- **安全漏洞分布图**：清晰展示安全问题的严重程度和分布

### 🛠️ 多维度分析能力
- **基础 Git 分析**：提交频率、作者活动、文件变更统计
- **高级代码分析**：函数复杂度、类设计质量、代码重复率
- **依赖健康检查**：过时的依赖包、潜在的安全风险
- **漏洞风险评估**：按严重程度分类的安全问题统计

## 📋 系统要求

- Python 3.7 或更高版本
- Git 版本控制系统
- 支持 Linux、macOS、Windows 系统

## 🚀 快速开始

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/RepositoryAnalyzer.git
cd RepositoryAnalyzer

# 安装依赖包
pip install -r requirements.txt
```

### 基本使用

```bash
# 直接运行分析（分析默认的 COMTool 项目）
python main.py

# 或者指定自定义仓库
python main.py --url https://github.com/your/project.git --path ./myrepo
```

### 配置选项

在 `main.py` 中可以配置以下参数：

```python
# 仓库配置
GIT_URL = "https://github.com/Neutree/COMTool.git"  # 要分析的仓库地址
REPO_PATH = "./repo"                                 # 本地存储路径
REPORT_DIR = "reports"                               # 报告输出目录
PREFIX = "comtool_"                                  # 报告文件前缀
```

## 📁 项目结构

```
RepositoryAnalyzer/
├── main.py                           # 主程序入口
├── html_generator.py                 # Git 树状图生成器
├── analysis_visualizer.py            # 分析结果可视化
├── analyze.py                        # 基础 Git 分析模块
├── code_analyzer.py                  # 代码复杂度分析
├── dependency_analyzer.py            # 依赖关系分析
├── vulnerability_scanner.py          # 安全漏洞扫描
├── repo/                             # 克隆的仓库存储目录
├── reports/                          # 分析报告输出目录
└── requirements.txt                  # 项目依赖
```

## 📈 分析结果

运行完成后，将在 `reports/` 目录下生成以下报告：

1. **Git 可视化页面**：`git_tree.html` - 交互式分支和提交历史图
2. **代码复杂度报告**：包含函数和类的复杂度分析
3. **依赖分析报告**：项目依赖包清单和版本信息
4. **安全漏洞报告**：发现的安全问题和建议修复方案
5. **统计分析图表**：各类数据的图表化展示

## 🔧 核心模块说明

### 1. Git 历史分析 (`analyze.py`)
- 提交历史统计
- 作者活动分析
- 文件变更追踪
- 分支合并分析

### 2. 代码复杂度分析 (`code_analyzer.py`)
- 使用 Radon 进行静态代码分析
- 计算圈复杂度(McCabe)
- 分析代码行数(LOC)
- 评估函数和类的设计质量

### 3. 依赖分析 (`dependency_analyzer.py`)
- 自动识别 Python 依赖包
- 分析依赖版本兼容性
- 检测过时的依赖项
- 可视化依赖关系图

### 4. 安全漏洞扫描 (`vulnerability_scanner.py`)
- 集成 Bandit 安全扫描工具
- 识别常见安全漏洞模式
- 按严重程度分类问题
- 提供修复建议

### 5. 可视化展示 (`analysis_visualizer.py`)
- 生成交互式图表
- 创建 HTML 报告
- 数据可视化展示
- 用户体验优化

## 🎯 使用场景

- **项目健康度评估**：定期分析项目的技术债务和代码质量
- **代码审查辅助**：在代码合并前进行质量检查
- **安全审计**：识别潜在的安全漏洞和风险
- **依赖管理**：跟踪和管理项目依赖的健康状况
- **开发效率分析**：了解团队的开发活动和代码演进