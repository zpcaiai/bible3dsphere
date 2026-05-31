# 诗歌资源生成脚本

把诗歌旋律渲染成五线谱图 + 合成音频，并导出跟唱时间轴。
依赖：`python3`、`numpy`、`Pillow`、`ffmpeg`(在 PATH)，以及中文字体
`DroidSansFallbackFull.ttf` 与 `DejaVuSans*`（Linux 常见，路径见各脚本顶部常量）。

## 数据
- `melodies.py` —— 9 首旋律(简谱/movable-do)：`(degree, octave, beats, lyric)`；
  `"|"`=小节线，`"//"`=跟唱换行。改旋律/歌词只动这里。

## 生成（在本目录运行）
```bash
python3 synth.py        # -> ../../public/hymns/<id>.mp3   (管风琴音色合成)
python3 staff.py        # -> ../../public/hymns/<id>.png   (五线谱)
python3 gen_timing.py   # -> ../../src/hymnTimings.js       (逐行+逐字时间轴)
```
单首调试：`python3 staff.py amazing-grace joy-to-the-world`

## 说明
当前 mp3/png 为脚本生成的 demo（旋律可识别、谱与音频一致）。
要换专业录音/正式乐谱，直接用同名文件覆盖 `public/hymns/<id>.{mp3,png}` 即可，
播放器无需改动；缺文件会优雅降级。
