诗歌资源目录
============
每首诗歌两个文件(文件名 = HymnPlayer.jsx 里的 id):
  <id>.mp3   音频(当前为本地合成的管风琴 demo)
  <id>.png   五线谱图片(当前为脚本渲染)
缺文件时播放器优雅降级(音频显示"待添加"，曲谱显示SVG占位)。
跟唱逐行高亮的时间轴在 src/hymnTimings.js(由旋律自动生成)。

当前内置 id:
  amazing-grace, it-is-well, how-great-thou-art, holy-holy-holy,
  blessed-assurance, safe-in-arms, joy-to-the-world, when-i-survey, mighty-fortress
