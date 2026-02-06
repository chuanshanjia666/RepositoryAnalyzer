# 大连理工大学学位论文模板 latexmk 配置文件

# 设置主文件名
$main_filename = "main";

# 使用 XeLaTeX 编译
$pdflatex = 'xelatex -shell-escape -synctex=1 -interaction=nonstopmode -file-line-error %O %S';

# 使用 biber 处理参考文献
$biber = 'biber %O %S';

# 自动生成PDF文件名
$pdf_mode = 1;

# 生成同步TeX文件，便于反向搜索
$synctex = 1;

# 不停止编译，即使有错误也继续
$max_repeat = 5;  # 最多重复编译5次

# 清理时保留的文件
$clean_ext = "run.xml";

# 自动检测是否需要运行 biber
add_cus_dep('bcf', 'bbl', 0, 'biber');

# 输出目录设置（如果需要）
# $out_dir = 'build';

# 日志文件设置
$log_file = 'latexmk.log';

# 编译完成后自动清理辅助文件
# $clean_full_ext = "bbl blg run.xml";

# PDF查看器设置（Linux）
$pdf_previewer = 'start xdg-open';

# Windows 系统设置
# $pdf_previewer = 'start acroread';

# macOS 系统设置
# $pdf_previewer = 'open';

# 编译后自动打开PDF（设为1启用）
$post_compile_view = 0;

# 编译后自动清理（设为1启用）
$clean_after_view = 0;