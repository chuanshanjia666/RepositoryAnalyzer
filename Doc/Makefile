# 大连理工大学学位论文模板 Makefile
# 使用 latexmk 自动化编译流程

# 编译器设置
LATEXMK = latexmk
PDFLATEX = xelatex
BIBER = biber

# 主文件名
MAIN = main

# 默认目标
all: pdf

# 生成PDF
pdf:
	$(LATEXMK) -$(PDFLATEX) -shell-escape -synctex=1 -interaction=nonstopmode -file-line-error $(MAIN).tex

# 清理临时文件
clean:
	$(LATEXMK) -c

# 彻底清理（包括PDF）
distclean: clean
	$(LATEXMK) -C

# 生成参考文献（如果需要的话）
bib:
	$(BIBER) $(MAIN)

# 查看PDF
view: pdf
	xdg-open $(MAIN).pdf || open $(MAIN).pdf || echo "无法自动打开PDF，请手动打开 $(MAIN).pdf"

# 快速编译（用于草稿查看）
quick:
	$(PDFLATEX) -shell-escape -interaction=nonstopmode $(MAIN).tex

# 检查拼写（需要 aspell 或 hunspell）
spell:
	aspell -t -c $(MAIN).tex || hunspell -t $(MAIN).tex || echo "需要安装 aspell 或 hunspell"

# 查看帮助
help:
	@echo "大连理工大学学位论文模板编译命令:"
	@echo "  make pdf      - 完整编译生成PDF（推荐）"
	@echo "  make quick    - 快速编译（仅一次XeLaTeX）"
	@echo "  make clean    - 清理临时文件"
	@echo "  make distclean- 彻底清理（包括PDF）"
	@echo "  make view     - 编译并打开PDF"
	@echo "  make bib      - 仅处理参考文献"
	@echo "  make spell    - 拼写检查"
	@echo "  make help     - 显示此帮助信息"

.PHONY: all pdf clean distclean bib view quick spell help