%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
%   大连理工大学硕士论文模板 —— 文档类文件 dlutthesis.cls
%   版本：1.0
%   最后更新：2024-01-01
%   编译环境：XeLaTeX + biblatex + biber
%   欢迎使用，如有任何意见和建议请发送邮件至 yuri_1985@163.com，感谢您的支持！
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{dlutthesis}[2024/01/01 v1.0 Dalian University of Technology Thesis Template]

% 基础文档类
\LoadClass[12pt,a4paper,openany,oneside]{book}

% 版面控制
\RequirePackage[body={16.1true cm,22.0true cm}]{geometry}   %论文版芯161mm×220mm（不包括页眉页脚）
\RequirePackage{indentfirst}    % 首行缩进宏包
\RequirePackage[sf]{titlesec}   % 控制标题的宏包
\RequirePackage{titletoc}       % 控制目录的宏包
\RequirePackage{fancyhdr}       % 自定义页眉页脚
\RequirePackage{fancyref}       % 引用链接属性
%\RequirePackage{cite}           % 支持引用的宏包（与 natbib 冲突，已禁用）
\RequirePackage[perpage,symbol]{footmisc}   % 脚注控制
\RequirePackage{layouts}        % 打印当前页面格式的宏包
\RequirePackage{paralist}       % 一种换行不缩进的列表格式，用 asparaenum 或者 inparaenum 环境
%\RequirePackage[numbers]{natbib}         % 参考文献（已替换为 biblatex）
\RequirePackage{fancyvrb}       % 原样输出
%\RequirePackage{listings}   % 粘贴源代码

% 字体
\RequirePackage[UTF8]{ctex}        % 中文支持宏包，使用 UTF-8 编码
\RequirePackage{amsmath}    % AMS 宏包，包含一些常用的数学字体和符号，
\RequirePackage{amssymb}    % 如果你引用一些不常见的字体宏包可能会与此发生冲突，请考虑略去。
\RequirePackage{mathrsfs}   % 一种常用于定义泛函算子的花体字母，只有大写。
\RequirePackage[amsmath,thmmarks,hyperref]{ntheorem} % 定理类环境宏包，其中 amsmath 选项用来兼容 AMS的宏包
\RequirePackage{type1cm}    % 控制字体的大小
\RequirePackage{bm}         % 处理数学公式中的黑斜体的宏包
%\RequirePackage{fourier}    % 一种和Times类似的字体
%\RequirePackage{txfonts}   % 如果你希望和 Word 的默认值保持一致，请使用此宏包（XeLaTeX 下不兼容）
\RequirePackage{helvet}

% 图形
\RequirePackage{graphicx}   % 这里引用 graphicx 宏包时没有图形驱动选项，所以请在引用图片时务必给出后缀名
\RequirePackage{subfigure}  % 插入子图形
\RequirePackage{color}      % 支持彩色
\RequirePackage[below]{placeins}    % 浮动图形控制宏包
%\RequirePackage{picinpar}   % 图文混排用宏包
%\RequirePackage{floatflt}  % 图文混排用宏包
\RequirePackage{rotating}   % 图形和表格的控制
\RequirePackage[subfigure]{ccaption}    % 浮动图形和表格标题样式，支持插图表格的双语标题
\RequirePackage{setspace}   % 定制表格和图形的多行标题行距！！

% 其他
\RequirePackage{calc}   % 在 tex 文件中具有一些计算功能，主要用在页面控制。
%\RequirePackage{ccmap}      % 使pdfLatex生成的文件支持复制等（XeLaTeX 不需要此包）
\RequirePackage[unicode,
            bookmarksnumbered=true,
            bookmarksopen=true,
            colorlinks=true,
            citecolor=blue,
            linkcolor=black,
            anchorcolor=green,
            urlcolor=blue,
            breaklinks=true
            ]{hyperref} % 生成有书签和超链接的 pdf，使用 unicode 支持 UTF-8

% 参考文献（使用现代的 biblatex + biber 方案）
\RequirePackage[backend=biber,style=gb7714-2015]{biblatex}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 页面设置
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% A4 纸张
\setlength{\paperwidth}{21.0cm}
\setlength{\paperheight}{29.7cm}
% 设置正文尺寸大小
\setlength{\textwidth}{16.1cm}
\setlength{\textheight}{22.2cm}
% 设置正文区在正中间
\newlength \mymargin
\setlength{\mymargin}{(\paperwidth-\textwidth)/2}
%\setlength{\sidemargin}{(\mymargin)-1in}
%\setlength{\evensidemargin}{(\mymargin)-1in}
% 设置正文区偏移量，奇数页向右偏，偶数页向左偏
\newlength \myshift
\setlength{\myshift}{0.35cm}     % 双面打印的奇偶页偏移值，可根据需要修改，建议小于 0.5 cm。
%\addtolength{\oddsidemargin}{\myshift}
%\addtolength{\evensidemargin}{-\myshift}
\setlength{\topmargin}{-0.05cm}
\setlength{\headheight}{0.50cm}
\setlength{\headsep}{0.90cm}
\setlength{\footskip}{1.47cm}
% 公式的精调
\allowdisplaybreaks[4]  % 可以让公式在排不下的时候分页排，这可避免页面有大段空白。

%下面这组命令使浮动对象的缺省值稍微宽松一点，从而防止幅度
%对象占据过多的文本页面，也可以防止在很大空白的浮动页上放置
%很小的图形。
\renewcommand{\textfraction}{0.15}
\renewcommand{\topfraction}{0.85}
\renewcommand{\bottomfraction}{0.65}
\renewcommand{\floatpagefraction}{0.60}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 字体字号定义
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 中文段落缩进和 ~ 字符替换
%\CJKindent                              % 首行缩进两个汉字（ctex 包自动处理）
\sloppy
%\CJKspace                              % 中英文混排的断行
%\CJKtilde                               % 重新定义~，用~隔开中英文（ctex 包自动处理）
% 中文字体 - 使用 ctex 包的标准字体命令
\newcommand{\song}{\songti}    % 宋体
\newcommand{\fs}{\fangsong}        % 仿宋
\newcommand{\kai}{\kaishu}      % 楷体
\newcommand{\hei}{\heiti}    % 黑体
\newcommand{\li}{\songti}        % 隶书（用宋体替代）
\newcommand{\you}{\songti}      % 幼圆（用宋体替代）
\newcommand{\hwxh}{\heiti}    % 华文细黑（用黑体替代）
% 字号
\newcommand{\yihao}{\fontsize{26pt}{39pt}\selectfont}               % 一号，1.5 倍行距
\newcommand{\xiaoyi}{\fontsize{24pt}{30pt}\selectfont}              % 小一，1.25倍行距
\newcommand{\erhao}{\fontsize{22pt}{27.5pt}\selectfont}             % 二号，1.25倍行距
\newcommand{\xiaoer}{\fontsize{18pt}{22.5pt}\selectfont}              % 小二，1.25倍行距
\newcommand{\sanhao}{\fontsize{16pt}{20pt}\selectfont}              % 三号，1.25倍行距
\newcommand{\xiaosan}{\fontsize{15pt}{18.75pt}\selectfont}          % 小三，1.25倍行距
\newcommand{\sihao}{\fontsize{14pt}{17pt}\selectfont}               % 四号，1.25倍行距
\newcommand{\xiaosi}{\fontsize{12pt}{15pt}\selectfont}              % 小四，1.25倍行距
\newcommand{\dawu}{\fontsize{10.5pt}{18pt}\selectfont}              % 五号，1.75倍行距
\newcommand{\zhongwu}{\fontsize{10.5pt}{15pt}\selectfont}           % 五号，1.5 倍行距
\newcommand{\wuhao}{\fontsize{10.5pt}{10.5pt}\selectfont}           % 五号，单倍行距
\newcommand{\xiaowu}{\fontsize{9pt}{9pt}\selectfont}                % 小五，单倍行距

% defaultfont 默认字体命令
\def\defaultfont{\renewcommand{\baselinestretch}{1.27}
\fontsize{12pt}{15pt}\selectfont}

% 设置目录字体和行间距
\def\defaultmenufont{\renewcommand{\baselinestretch}{1.22}
\fontsize{12pt}{15pt}\selectfont}

% 固定距离内容填入及下划线
\makeatletter
    \newcommand\fixeddistanceleft[2][1cm]{{\hb@xt@ #1{#2\hss}}}
    \newcommand\fixeddistancecenter[2][1cm]{{\hb@xt@ #1{\hss#2\hss}}}
    \newcommand\fixeddistanceright[2][1cm]{{\hb@xt@ #1{\hss#2}}}
    \newcommand\fixedunderlineleft[2][1cm]{\underline{\hb@xt@ #1{#2\hss}}}
    \newcommand\fixedunderlinecenter[2][1cm]{\underline{\hb@xt@ #1{\hss#2\hss}}}
    \newcommand\fixedunderlineright[2][1cm]{\underline{\hb@xt@ #1{\hss#2}}}
    \newcommand\fixedunderlinemultiline[2][1cm]{\underline{\parbox[t]{#1}{\raggedright#2}}}
\makeatother

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 标题相关
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 定义、定理等环境
\theoremstyle{plain}
\theoremheaderfont{\hei\bf}
\theorembodyfont{\song\rmfamily}
\newtheorem{definition}{\hei 定义}[chapter]
\newtheorem{example}{\hei 例}[chapter]
\newtheorem{algorithm}{\hei 算法}[chapter]
\newtheorem{theorem}{\hei 定理}[chapter]
\newtheorem{axiom}{\hei 公理}[chapter]
\newtheorem{proposition}[theorem]{\hei 命题}
\newtheorem{property}{\hei 性质}
\newtheorem{lemma}[theorem]{\hei 引理}
\newtheorem{corollary}{\hei 推论}[chapter]
\newtheorem{remark}{\hei 注解}[chapter]
\newenvironment{proof}{{\hei证明　}}%
{\hfill $\square$ \vskip 4mm}
%\theoremsymbol{$\square$}

% 目录标题
\renewcommand\contentsname{\hfill 目　　录 \hfill}
\renewcommand\listfigurename{\hfill 插~图~目~录 \hfill}
\renewcommand\listtablename{\hfill 表~格~目~录 \hfill}
\renewcommand{\bibname}{\hfill 参~考~文~献 \hfill}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 段落章节
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\setcounter{secnumdepth}{4}
\setcounter{tocdepth}{4}
% 设置章、节、小节、小小节的间距
\titleformat{\chapter}[hang]{\normalfont\xiaosan\hei}{\xiaosan\thechapter}{10pt}{\xiaosan}
\titlespacing{\chapter}{0pt}{-3ex  plus .1ex minus .2ex}{3.3ex}
\titleformat{\section}[hang]{\sihao\hei}{\sihao\thesection}{0.5em}{}{}
\titlespacing{\section}{0pt}{0.5em}{0.5em}
\titleformat{\subsection}[hang]{\xiaosi\hei\sf}{\xiaosi\thesubsection}{0.5em}{}{}
\titlespacing{\subsection}{0pt}{0.5em}{0.3em}
\titleformat{\subsubsection}[hang]{\hei\sf}{\thesubsubsection}{0.5em}{}{}
\titlespacing{\subsubsection}{0pt}{0.3em}{0pt}
% 缩小目录中各级标题之间的缩进
\dottedcontents{chapter}[0.32cm]{\vspace{0.2em}}{1.0em}{5pt}
\dottedcontents{section}[1.32cm]{}{1.8em}{5pt}
\dottedcontents{subsection}[2.32cm]{}{2.7em}{5pt}
\dottedcontents{subsubsection}[3.32cm]{}{3.4em}{5pt}

% 段落之间的竖直距离
\setlength{\parskip}{1.2pt}
% 定义行距
\renewcommand{\baselinestretch}{1.27}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 页眉和页脚 使用 fancyhdr 宏包
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newcommand{\makeheadrule}{%
    \makebox[0pt][l]{\rule[.7\baselineskip]{\headwidth}{0.5pt}}%
    \vskip-.8\baselineskip}

\makeatletter
\renewcommand{\headrule}{%
    {\if@fancyplain\let\headrulewidth\plainheadrulewidth\fi
     \makeheadrule}}

\pagestyle{fancyplain}

\fancyhf{}
\fancyhead[C]{\songti\wuhao 大连理工大学本科毕业设计（论文）题目}
%\fancyhead[CE]{\songti\wuhao\@ctitle}
\fancyfoot[C]{\xiaowu--~\thepage~--}

% Clear Header Style on the Last Empty Odd pages
\makeatletter
\def\cleardoublepage{\clearpage\if@twoside \ifodd\c@page\else%
    \hbox{}%
    \thispagestyle{empty}%              % Empty header styles
    \newpage%
    \if@twocolumn\hbox{}\newpage\fi\fi\fi}



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 调整列表环境的垂直间距
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\let\orig@Itemize =\itemize
\let\orig@Enumerate =\enumerate
\let\orig@Description =\description

\def\Myspacing{\itemsep=1ex \topsep=-4ex \partopsep=-2ex \parskip=-1ex \parsep=2ex}
\def\newitemsep{
\renewenvironment{itemize}{\orig@Itemize\Myspacing}{\endlist}
\renewenvironment{enumerate}{\orig@Enumerate\Myspacing}{\endlist}
\renewenvironment{description}{\orig@Description\Myspacing}{\endlist}
}
\def\olditemsep{
\renewenvironment{itemize}{\orig@Itemize}{\endlist}
\renewenvironment{enumerate}{\orig@Enumerate}{\endlist}
\renewenvironment{description}{\orig@Description}{\endlist}
}
\renewcommand{\labelenumi}{(\arabic{enumi})}
\newitemsep

% fancyvrb宏包中\VerbatimInput的格式设置
\fvset{fontsize=\small, frame=single, baselinestretch=1}

% 修改引用的格式
\newcommand{\ucite}[1]{$^{\mbox{\scriptsize \citep{#1}}}$} % 增加 \ucite 命令使显示的引用为上标形式
\newcommand{\citeup}[1]{$^{\mbox{\scriptsize \citep{#1}}}$} % for WinEdt users

%参考文献
%\addtolength{\bibsep}{-0.2cm}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 图形表格
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}
%\captionstyle{\centering}
%\hangcaption
\captiondelim{\hspace{1em}}
\captionnamefont{\song\rmfamily\zhongwu\selectfont}
\captiontitlefont{\song\rmfamily\zhongwu\selectfont}

\newcommand{\tablepage}[2]{\begin{minipage}{#1}\vspace{0.5ex} #2 \vspace{0.5ex}\end{minipage}}
\newcommand{\returnpage}[2]{\begin{minipage}{#1}\vspace{0.5ex} #2 \vspace{-1.5ex}\end{minipage}}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 定义题头格言的格式
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newsavebox{\AphorismAuthor}
\newenvironment{Aphorism}[1]
{\vspace{0.5cm}\begin{sloppypar} \slshape
\sbox{\AphorismAuthor}{#1}
\begin{quote}\small\itshape }
{\\ \hspace*{\fill}------\hspace{0.2cm} \usebox{\AphorismAuthor}
\end{quote}
\end{sloppypar}\vspace{0.5cm}}

%自定义一个空命令，用于注释掉文本中不需要的部分。
\newcommand{\comment}[1]{}

% This is the flag for longer version
\newcommand{\longer}[2]{#1}

\newcommand{\ds}{\displaystyle}

% define graph scale
\def\gs{1.0}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 自定义项目列表标签及格式 \begin{denselist} 列表项 \end{denselist}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\newcounter{newlist} %自定义新计数器
\newenvironment{denselist}[1][temp]{%%%%%定义新环境：可改变的列表题目
\begin{list}{\textbf{#1} (\arabic{newlist})} %%标签格式
    {
    \usecounter{newlist}
     \setlength{\labelwidth}{22pt} %标签盒子宽度
     \setlength{\labelsep}{0cm} %标签与列表文本距离
     \setlength{\leftmargin}{0cm} %左右边界
     \setlength{\rightmargin}{0cm}
     \setlength{\parsep}{0ex} %段落间距
     \setlength{\itemsep}{0ex} %标签间距
     \setlength{\itemindent}{44pt} %标签缩进量
     \setlength{\listparindent}{44pt} %段落缩进量
    }}
{\end{list}}%%%%%

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 封面摘要
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\def\cdegree#1{\def\@cdegree{#1}}\def\@cdegree{}
\def\ctitle#1{\def\@ctitle{#1}}\def\@ctitle{}
\def\caffil#1{\def\@caffil{#1}}\def\@caffil{}
\def\csubject#1{\def\@csubject{#1}}\def\@csubject{}
\def\cschool#1{\def\@cschool{#1}}\def\@cschool{}
\def\creviewer#1{\def\@creviewer{#1}}\def\@creviewer{}
\def\cauthor#1{\def\@cauthor{#1}}\def\@cauthor{}
\def\cauthorno#1{\def\@cauthorno{#1}}\def\@cauthorno{}
\def\csupervisor#1{\def\@csupervisor{#1}}\def\@csupervisor{}
\def\cdate#1{\def\@cdate{#1}}\def\@cdate{}
\long\def\cabstract#1{\long\def\@cabstract{#1}}\long\def\@cabstract{}
\def\ckeywords#1{\def\@ckeywords{#1}}\def\@ckeywords{}
\def\etitle#1{\def\@etitle{#1}}\def\@etitle{}
\long\def\eabstract#1{\long\def\@eabstract{#1}}\long\def\@eabstract{}
\def\ekeywords#1{\def\@ekeywords{#1}}\def\@ekeywords{}

\def\originality{
    \renewcommand{\baselinestretch}{1.61}
    % 独创性说明
    \newpage
    \thispagestyle{empty}
    \begin{center}
        \parbox[t][1.52cm][c]{\textwidth}{{\xiaoer\song\centerline{大连理工大学学位论文独创性声明}}}
        \parbox[t][7.68cm][c]{\textwidth}{\sihao\fs
            作者郑重声明：所呈交的学位论文，是本人在导师的指导下进行研究工作所取得的成果。%
            尽我所知，除文中已经注明引用内容和致谢的地方外，%
            本论文不包含其他个人或集体已经发表的研究成果，%
            也不包含其他已申请学位或其他用途使用过的成果。%
            与我一同工作的同志对本研究所做的贡献均已在论文中做了明确的说明并表示了谢意。%

            \vspace{0.47cm}
            若有不实之处，本人愿意承担相关法律责任。
        }
        \parbox[t][0.58cm][c]{\textwidth}
        {\sihao\fs 学{\hfill}位{\hfill}论{\hfill}文{\hfill}题{\hfill}目{\hfill}：\fixedunderlinecenter[12.6cm]{\@ctitle}}
        \parbox[t][1.22cm][c]{\textwidth}
        {\sihao\fs 作{\hfill}者{\hfill}签{\hfill}名{\hfill}：\fixeddistanceleft[12.6cm]{\underline{\hspace{5.8cm}}\hfill
               日期：\underline{\hspace{1.4cm}}~年~{\underline{\hspace{0.7cm}}~月~{\underline{\hspace{0.7cm}}~日~}}}}
    \end{center}
    \renewcommand{\baselinestretch}{1.27}
    \cleardoublepage
}

\def\makecover{
    \begin{titlepage}
    % 中文封面
        \newpage
        \thispagestyle{empty}
            \begin{center}
            \parbox[t][4.34cm][c]{\textwidth}
            {
                \begin{center}
                    {\xiaoyi\song\textbf{\@cdegree}\\}
                    \vspace{1.36cm}
                    {\erhao\hwxh\bf{\@ctitle}\\}
                    \vspace{0.17cm}
                    {\sanhao\textbf{\@etitle}\\}
                \end{center}
            }
            \parbox[b][10.39cm][c]{\textwidth}
            {
                \vspace{8.2cm}
                \begin{center}
                    \xiaosan\song
                    \begin{tabular}{p{0.6cm}p{6.7em}@{\extracolsep{0.4em}}lc}
                        \vspace{0.18cm}
                        ~ & 学 院（学部）：& \fixedunderlineleft[6.08cm]{\@cschool} &
\\
                         \vspace{0.18cm}
                         ~ & 专 \hfill  业：& \fixedunderlineleft[6.08cm]{\@csubject} & \\
                         \vspace{0.18cm}
                        ~ & 学 \hfill 生 \hfill 姓 \hfill 名：& \fixedunderlineleft[6.08cm]{\@cauthor} & \\
                        \vspace{0.18cm}
                        ~ & 学 \hfill 号：& \fixedunderlinemultiline[6.08cm]{\@cauthorno} & \\
                        \vspace{0.18cm}
                        ~ & 指 \hfill 导 \hfill 教 \hfill 师：& \fixedunderlineleft[6.08cm]{\@csupervisor} & \\
                        \vspace{0.18cm}
                        ~ & 评 \hfill 阅 \hfill 教 \hfill 师：& \fixedunderlineleft[6.08cm]{\@creviewer} & \\
                        \vspace{0.18cm}
                        ~ & 完 \hfill 成 \hfill 日 \hfill 期：& \fixedunderlineleft[6.08cm]{\@cdate} & \\
                        \vspace{0.18cm}
                    \end{tabular}
                \end{center}
            }

            \vspace{4.88cm}

            {
            \begin{figure}[h]
                \centering
                \includegraphics[scale=1]{dlut.pdf}
            \end{figure}
            \vspace{-0.35cm}
            \xiaosi\song{Dalian University of Technology}
            }
            \end{center}
        \cleardoublepage
    \end{titlepage}
}

\def\authorization
{
\begin{center}
    \sanhao\hei~大连理工大学学位论文版权使用授权书~
\end{center}

\sihao\fs\noindent
　　本人完全了解学校有关学位论文知识产权的规定，%
在校攻读学位期间论文工作的知识产权属于大连理工大学，允许论文被查阅和借阅。%
学校有权保留论文并向国家有关部门或机构送交论文的复印件和电子版，%
可以将本学位论文的全部或部分内容编入有关数据库进行检索，%
可以采用影印、缩印、或扫描等复制手段保存和汇编本学位论文。%
\\

\vspace{0.2cm}\noindent
学{\hfill}位{\hfill}论{\hfill}文{\hfill}题{\hfill}目{\hfill}：\fixedunderlinecenter[12.6cm]{\@ctitle}\\
作{\hfill}者{\hfill}签{\hfill}名{\hfill}：\fixeddistanceleft[12.6cm]{\underline{\hspace{5.8cm}}\hfill
    日期：\underline{\hspace{1.4cm}}~年~{\underline{\hspace{0.7cm}}~月~{\underline{\hspace{0.7cm}}~日~}}}\\
导{\hfill}师{\hfill}签{\hfill}名{\hfill}：\fixeddistanceleft[12.6cm]{\underline{\hspace{5.8cm}}\hfill
	 日期：\underline{\hspace{1.4cm}}~年~{\underline{\hspace{0.7cm}}~月~{\underline{\hspace{0.7cm}}~日~}}}\\
\renewcommand{\baselinestretch}{1.27}
}

\def \makeabstract{
    \defaultfont

    \chapter*{\hfill 摘　　要 \hfill}
    \addcontentsline{toc}{chapter}{摘　　要}
    \setcounter{page}{1}
    \@cabstract
    \vspace{0.53cm}

    \noindent {\hei\bf{关键词：{\fs\@ckeywords}}}

    \defaultfont
    \cleardoublepage
    \chapter*{}
    \addcontentsline{toc}{chapter}{Abstract}
    \vspace{-1.38cm}
    \begin{center}
        {\xiaosan\textrm{\textbf{\@etitle}}}
    \end{center}
    \vspace{-0.36cm}
    \begin{center}
    {
       \xiaosan{Abstract}\\
    }
    \end{center}
    \vspace{0.11cm}

    \@eabstract

    \vspace{0.55cm}

    \noindent {\bf{Key Words:}} ~~ {\textsc{\@ekeywords}}
    \cleardoublepage
}

\makeatletter
\def\hlinewd#1{%
  \noalign{\ifnum0=`}\fi\hrule \@height #1 \futurelet
   \reserved@a\@xhline}
\makeatother

%定义索引生成
\def\generateindex
{
    \addcontentsline{toc}{chapter}{\indexname}
    \printindex
    \cleardoublepage
}

\raggedbottom

% 文档类文件结束

\endinput