#!/bin/bash
# LaTeX 完整编译脚本

echo "正在编译 main.tex..."
echo "步骤 1/4: 第一次 XeLaTeX 编译..."
xelatex main.tex

echo "步骤 2/4: 运行 Biber 生成参考文献..."
biber main

echo "步骤 3/4: 第二次 XeLaTeX 编译..."
xelatex main.tex

echo "步骤 4/4: 第三次 XeLaTeX 编译..."
xelatex main.tex

echo "编译完成！生成的 PDF 文件: main.pdf"
