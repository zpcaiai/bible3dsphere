属灵书籍 PDF 目录
================
把书的 PDF 放在这里（会被网站当静态文件，访问路径 /book/<文件名>.pdf）。
然后在 src/SpiritualBooksPage.jsx 的 BOOKS 数组里加一条：
  { id:'唯一id', title:'书名', author:'作者', emoji:'📖', color:'#5ac8fa',
    kind:'pdf', pdf:'/book/你的文件.pdf', blurb:'简介',
    chapters:[{title:'第一章', text:'正文…'}] }   // chapters 可选，提供文字才能语音朗读

当前内置：
  晨恩日新（复用日历阅读器，已含全文+语音；若放 晨恩日新.pdf 在此，可在书内点「PDF」查看）
