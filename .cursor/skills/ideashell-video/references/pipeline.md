# 渲染流水线与工具速查

## 数据流

```
<slug>_timeline.py ──► <slug>_render.py ──(raw RGB 帧, stdin)──► ffmpeg ──► out/<slug>-video.mp4 ─┐
        │                                                                                         ├─► ffmpeg 合成 ─► dist/ideashell-<slug>.mp4
        └────────────► <slug>_audio.py ──► out/<slug>-audio.wav ──────────────────────────────────┘
```

- `render(t)` 是纯函数：给一个时间（秒），返回一张 1080×1920 的 RGB 图，跟上一帧无关。所以可以随便跳到任意时间出静帧，也能多进程并行渲染。
- 时间只在 timeline 文件里定义，画面和音效都从那里读，改一个常量两边一起动。
- 布局按 1080×1920 满幅写，最后 `xhs_safe(img, PAPER)` 统一缩放、下移，留出小红书的安全区。

## 环境

依赖 Python 3、Pillow、numpy 和 ffmpeg：

```bash
pip install pillow numpy
```

字体（Noto Sans SC，约 34 MB）由 `build_*.sh` 自动下载到 `fonts/`，不进仓库。`out/` 是中间产物，也不进仓库；`dist/` 是成片，要提交。

## `render.py` 里的工具

### 时间与缓动

| 函数 | 作用 |
| --- | --- |
| `prog(t, start, dur)` | 返回 0→1 的线性进度，超出范围会截断 |
| `clamp(v, lo, hi)`、`lerp(a, b, p)` | 截断、插值 |
| `out_cubic`、`in_cubic`、`in_out`、`out_back(p, s)` | 缓动函数。`out_back` 会略微冲过头再弹回 |
| `appear(t, t0, dur, rise, from_scale)` | 标准弹入，返回 `(alpha, scale, dy)`，直接交给 `put` |

### 绘制

| 函数 | 作用 |
| --- | --- |
| `txt(s, size, weight, color)` | 单色文字图。weight 可以是 Regular / Medium / Bold / Black |
| `rich(((s, color), ...), size, weight)` | 多色文字，例如「帮你记，」黑色 +「帮你做」橙色 |
| `text_width(s, size, weight)` | 量文字宽度，用来居中或左对齐 |
| `rrect(w, h, r, fill, outline, width)` | 圆角矩形（2 倍超采样抗锯齿） |
| `circle(d, fill)`、`ring(r, width, color)` | 圆形、圆环 |
| `check_icon`、`check_badge(d)`、`sparkle`、`spinner`、`mic_icon` | 小图标 |
| `with_shadow(img, blur, dy, opacity)` | 加投影，返回 `(img, pad)` |
| `Card(w, h)` | 带投影的卡片，用 `.add(...)` 往上贴内容 |
| `asset(name, height=...)` | 读 `assets/<name>.png`：logo、phone-zh、mac-zh、watch-zh、mac-frame |
| `put(dst, img, x, y, scale, alpha, ax, ay, rotate)` | 把图贴到画布上。默认以 `(x, y)` 为中心；`ax=0` 表示左对齐 |
| `xhs_safe(img, bg)` | 最后一步，套用小红书安全区 |

带 `@lru_cache` 的函数返回的是共享的缓存图。要在返回的图上继续画，先 `.copy()`。

### 颜色（`timeline.py`）

`ORANGE (255,66,0)`、`ORANGE_SOFT`、`INK`、`GRAY`、`PAPER`、`LINE`、`RED`、`WHITE`。日程片在 `schedule_render.py` 里另有一套稿纸色：`PAPER (246,242,236)`、`CELL_FILL`、`CELL_LINE`、`MUTED`、`ROSE`，表示口头禅和改口。

## `audio.py` 里的工具

| 函数 | 作用 |
| --- | --- |
| `hz(midi)` | MIDI 音高转频率 |
| `pluck`、`pad`、`bass`、`bell` | 拨弦、铺底、贝斯、铃声 |
| `kick`、`hat`、`clap` | 鼓组 |
| `whoosh(dur, lo, hi, rising)`、`sweep_tone(f0, f1, dur, decay)` | 风声、扫频 |
| `mixs(*parts)` | 把几段长度不同的声音叠在一起 |
| `reverb(x, seconds, mix)` | 混响 |
| `make_sfx(kind)` | 现成音效：`pop` `pop_hi` `tick` `check` `chime` `whoosh` `swipe` `rise` `mark` `marker` `snap` `drop` `sparkle` `impact` `zap0..` `ping0..3`，返回 `(signal, pan)` |

日程片的 `schedule_audio.py` 在这些基础上又做了打字声 `key`、标红连击 `markN`、吹走声 `blow`、落位声 `landN`、重音 `slam` 等，可以直接拿来用。

## 常用命令

```bash
python3 <slug>_render.py --stills 1 4.5 9   # 出静帧到 out/
./build_<slug>.sh                           # 完整出片
python3 cover.py                            # 日程片封面（新片子仿照它写一个）
```

完整渲染一条 30 秒的片子，在 4 核机器上大约 15–60 秒，取决于画面复杂度。
