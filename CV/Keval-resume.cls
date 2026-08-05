% Intro Options
\ProvidesClass{Keval-resume}[Resume class]
\NeedsTeXFormat{LaTeX2e}
\DeclareOption{print}{\def\@cv@print{}}
\DeclareOption*{%
  \PassOptionsToClass{\CurrentOption}{article}
}
\ProcessOptions\relax
\LoadClass{article}

% Package Imports
\usepackage[hmargin=0.5in, vmargin=0.6in]{geometry}
\usepackage[hidelinks]{hyperref}

%-------------------------------------------------------------------------------
%                3rd party packages
%-------------------------------------------------------------------------------
% Needed to make fixed length table
\RequirePackage{array}
% Needed to handle list environment
\RequirePackage{enumitem}
% Needed to handle text alignment
\RequirePackage{ragged2e}
% Needed to change line spacing in specific environment
\RequirePackage{setspace}

% Color definitions
\usepackage[usenames,dvipsnames]{xcolor} 
\definecolor{primary}{HTML}{2b2b2b}

% Set main fonts
\usepackage{fontspec}
% \defaultfontfeatures{Ligatures={NoCommon, NoDiscretionary, NoHistoric, NoRequired, NoContextual}}
% \setmainfont[Ligatures=TeX, Color=primary, Path = fonts/lato/, BoldItalicFont=Lato-RegIta, BoldFont=Lato-Reg, ItalicFont=Lato-LigIta]{Lato-Lig}
\setmainfont[Ligatures=TeX, Color=primary, Path = fonts/georgia/, Extension = .ttf, BoldItalicFont=georgiaz, BoldFont=georgiab, ItalicFont=georgiai]{georgia}
% \setmainfont[Ligatures=TeX, Color=primary]{Nimbus Roman}

% Define an environment for cvitems
\newenvironment{cvitems}{%
  \vspace{-2.5mm}
  \begin{justify}
  \begin{itemize}[
  leftmargin=3ex, 
  nosep, noitemsep]
    \setlength{\parskip}{0pt}
    % \renewcommand{\labelitemi}{\bullet}
}{%
  \end{itemize}
  \end{justify}
  \vspace{-4.0mm}
}

% Name command
\newcommand{\namesection}[2]{
\centering{\fontsize{16pt}{18pt}\selectfont\bfseries #1}\\
\vspace{1.5pt}
\centering{\fontsize{11pt}{14pt}\selectfont #2}\vspace{-3pt}}

% Section seperators 
\usepackage{titlesec}
\titlespacing{\section}{0pt}{0pt}{-8pt}
\titlespacing{\subsection}{0pt}{0pt}{0pt}
\newcommand{\sectionsep}{\vspace{8pt}}
\newcommand{\postsectionsep}{\vspace{4pt}}

% Headings command
\titleformat{\section}{
\scshape
% \fontspec[Path = fonts/georgia/]{georgia}
\fontsize{13pt}{15pt}\selectfont \raggedright\uppercase}{}{0em}{}

% Subheadings command
\titleformat{\subsection}{
% 	\fontspec[Path = fonts/lato/]{Lato-Bol}
	\fontsize{10pt}{11pt}\selectfont 
	\bfseries
}{}{0em}{}

\newcommand{\position}[2]{
% 	\fontspec[Path = fonts/georgia/]{georgiai}
	\fontsize{10pt}{11pt}\selectfont
% 	\textit{\textbf{#1}}
    % \emph{#1}
    #1
	\normalfont \hfill #2 \\
}

% Descriptors command
\newcommand{\descript}[1]{
\raggedright\scshape
% \fontspec[Path = fonts/lato/]{Lato-Bol}
\fontsize{10pt}{11pt}\selectfont {} \normalfont}
