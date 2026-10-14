# 闪念贝壳竖屏动效视频 · 操作手册

这份手册只做一种视频：竖屏产品动效短片。参照 `dist/ideashell-schedule.mp4`（「说话乱七八糟，日程井井有条」）：一个字一格打出来，口头禅和改口标红后被吹走，剩下的字飞进待办，再排进日历，最后是 logo、「帮你记，帮你做」和设备落版。宣传片和记忆片是同一套做法、不同分镜。

不解析链接，不拆帖子文案，不读取作者、点赞或评论。用户发来参考视频，只看节奏、版式和动效。

这份手册不绑定任何一个工具。Cursor、Grok，以及任何能打开本仓库、能执行命令的 Agent（包括跑 Opus 5.5 的 Claude），用的是同一份。成片质量来自下面的流程和 `ideashell-video/` 里的代码，不来自某个编辑器的专有功能。

用户若说「按公司的视频做法」或「按我们的视频做法」，就是指本文件。运营同学不会说文件名，你自己来读。

## 怎么开始

把仓库交给 Agent，第一句这样说：

> 按 ideashell-video/PLAYBOOK.md 做。先读完这份手册和它链接的文件，再开始。标了「停」的步骤要等我确认。主题是：……

三个入口，结果应一致：

| 工具 | 怎么把手册交给它 |
| --- | --- |
| Cursor | 打开本仓库直接说上面那句。仓库里的 Skill 只会把 Agent 指到本文件，规则不写在 Skill 里。 |
| Grok | 让 Grok 能读到本仓库（或把本文件和 `playbook/` 目录一并附上），第一句用上面那句。 |
| Claude / 其他 Opus 5.5 Agent | 同样把仓库交给它，第一句指向本文件。不需要 Cursor。 |

## 这套做法

所有视频都在 `ideashell-video/` 里：时间轴文件 → 逐帧渲染 → 合成音频 → ffmpeg 合成。没有剪辑软件，也没有人声。改一个数字重跑一次就能出新版。

已有的三条片子可以当范例读：

| 成片 | 时间轴 | 画面 | 音频 | 构建 |
| --- | --- | --- | --- | --- |
| 30s 宣传片 `dist/ideashell-promo.mp4` | `timeline.py` | `render.py` | `audio.py` | `build.sh` |
| 32s 记忆能力 `dist/ideashell-memory.mp4` | `memory_timeline.py` | `memory_render.py` | `memory_audio.py` | `build_memory.sh` |
| 28s 日程 `dist/ideashell-schedule.mp4` | `schedule_timeline.py` | `schedule_render.py` | `schedule_audio.py` | `build_schedule.sh` |

新片子从模板起步，不要从空文件写。

## 硬规则

- 规格：9:16，1080×1920，30 fps，H.264 yuv420p，crf 17，AAC 192k，`+faststart`。
- 全片不配人声，只有配乐和音效。响度约 -14 LUFS。
- 品牌橙 `#FF4200`，代码里是 `timeline.ORANGE = (255, 66, 0)`。字体只用 Noto Sans SC（Regular / Medium / Bold / Black）。
- 文案里不写「超过百万用户」这类用户规模说法。
- 落版用产品口号（现在是「帮你记，帮你做」），配 logo、「闪念贝壳」和「应用商店搜「闪念贝壳」」。
- 每一帧最后都要经过 `render.xhs_safe(img, PAPER)`。小红书会把视频铺到状态栏和返回 / 分享按钮下面，两边还会各裁掉约 70px。这个函数会把画面缩到 86% 再往下移 205px。布局照 1080×1920 满幅写，不用自己算边距。

## 流程

照顺序走。标「停」的步骤要等用户确认再往下。

### 1. 问清需求

要确认这几件事：主题一句话、时长、比例、平台（默认小红书）、落版长什么样、要不要参考视频。用户已经说了的就别再问。用户给了落版截图的话，量出截图里的位置和比例，照着还原。

### 2. 拆参考视频（有参考时）

照 [playbook/reference-teardown.md](playbook/reference-teardown.md) 做。只用用户给出的视频文件，看节奏、版式、配色和音效卡点。不抓取链接，不摘文案。

### 3. 写分镜（停）

先给用户一张分镜表：时间段、段落名、画面里发生什么、屏幕上出现的字、音效卡点。格式参照 `ideashell-video/README.md` 里现有的表。用户确认后再写代码。

### 4. 起项目

```bash
cd ideashell-video
python3 new_video.py <slug> "<主题>"   # slug 用小写字母加下划线，例如 todo_demo
./build_<slug>.sh                      # 先跑通，生成一条 12 秒的示例片
```

环境需要 Python 3、Pillow、numpy、ffmpeg。字体由构建脚本自动下载。

生成的四个文件：

- `<slug>_timeline.py`：所有时间点和文案，还有 `sfx_events()`。画面和声音都从这里读时间。
- `<slug>_render.py`：每个段落一个 `scene_*` 函数，`render(t)` 决定 t 秒画哪些段落。
- `<slug>_audio.py`：配乐和音效，音效名对应 `audio.make_sfx`。
- `build_<slug>.sh`：下载字体，依次生成音频、画面，合成到 `dist/ideashell-<slug>.mp4`。

### 5. 先定时间轴，再画画面

1. 把分镜写进 `<slug>_timeline.py`。每个动作一个具名常量（例如 `TASK1 = 5.55`），不要在渲染代码里写死数字。
2. 每个段落写成一个 `scene_*(img, t)`，用 `prog` / `appear` / 缓动函数算进度。可用的绘图工具见 [playbook/pipeline.md](playbook/pipeline.md)。
3. 每改一处就出几张静帧看：`python3 <slug>_render.py --stills 1.5 6 11`。静帧在 `out/`，要真的打开图片看。
4. 一个段落满意了再写下一个。

### 6. 配乐和音效

- 每个视觉动作在 `sfx_events()` 里配一个音效，例如打字配 `tick`、弹出配 `pop`、勾选配 `check`、落版配 `logo`。
- 段落切换的地方可以加一拍静音或一个重音，比连续铺满更有节奏感。
- 测响度：`ffmpeg -nostats -i dist/ideashell-<slug>.mp4 -af ebur128 -f null - 2>&1 | grep -A1 Integrated`。目标约 -14 LUFS，不够就调 `main()` 里 `tanh` 的 drive。

### 7. 出片和自检（停）

跑 `./build_<slug>.sh`，然后照 [playbook/qa-checklist.md](playbook/qa-checklist.md) 一条条查。检查要用成片里抽出来的帧，不看渲染前的静帧。如果用了自动审片，它指出的问题要先抽帧核实，确认是真的再改。

### 8. 封面

做两张：`cover-9x16.png`（1080×1920）和 `cover-3x4.png`（1080×1440）。直接复用视频里的绘制函数拼，可以参考 `ideashell-video/cover.py`。封面只在信息流里显示，不用套 `xhs_safe`，但主标题要放在画面中部，3:4 裁切后也能看全。

### 9. 交付

- 在 `ideashell-video/README.md` 里给新片子加一节：一句话简介、分镜表、怎么重新生成。
- 提交代码和 `dist/` 里的成片，一个逻辑改动一个 commit。
- 跟用户说成片和封面的路径，再列出这一版改了什么。

## 常见坑

- `rrect`、`txt`、`asset` 等函数带 `lru_cache`，返回的是共享的缓存图。要在上面继续画，先 `.copy()`，否则会改坏缓存，文字一帧帧叠在一起。
- 要从下往上叠：卡片先画，飞进卡片的字后画，不然字会被卡片挡住。
- 半透明的东西在飞行中会透出底下的格子。飞行时要么不透明，要么提前淡入。
- 英文和数字要整词放进一个格子（`cells_of` 的正则 `[A-Za-z0-9]+|.`），格子装不下时用 `fit=False` 或换版式，别把字缩小。
- 日历 / 表格里的块要对齐到行，不能跨两行。
- 改完版式，只要往画面下半部分加了东西，就抽成片最后 100px 看一眼，确认没有黑边或被裁掉。
- 渲染用 `multiprocessing.Pool(3)`。全局状态要在模块加载时建好，或者用 `lru_cache` 惰性生成，不能在 `main()` 里赋值，否则子进程拿到的是 None。
