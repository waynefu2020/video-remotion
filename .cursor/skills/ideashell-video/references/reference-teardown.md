# 拆解参考视频

目标是弄清参考视频「为什么好看」：节奏、版式、配色、动效语言、音效卡点。文案和具体画面不照抄。

## 1. 拿到视频文件

**有链接时：** 先用仓库里的「镜析」读出作者、正文和互动数据。在仓库根目录运行 `npm run dev`，然后打开 <http://127.0.0.1:43123> 贴链接。

**要视频文件本身（小红书）：** 用 TikHub 接口。令牌在 `.env.local`，每次请求都计费，不要循环重试。

```bash
set -a && . ./.env.local && set +a
curl -s -G "$TIKHUB_BASE_URL/api/v1/xiaohongshu/app_v2/search_notes" \
  --data-urlencode "keyword=<笔记标题里的关键词>" \
  -H "Authorization: Bearer $TIKHUB_TOKEN_XIAOHONGSHU" > /tmp/search.json
```

在返回结果里找到对应笔记。几个关键字段：

- 原始尺寸：`video_info_v2.media.video.width` / `height`
- 视频流地址：`video_info_v2.media.stream.h264[0]`（没有就用 `h265[0]`）里的 `master_url`

```bash
curl -L -o /tmp/ref.mp4 "<流地址>"
```

**用户直接发了视频文件时：** 跳过这一步。

## 2. 看规格

```bash
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,duration -of compact /tmp/ref.mp4
```

## 3. 联系表：一眼看完整片节奏

每 0.5 秒抽一帧，拼成 8×4 的一张图（16 秒以内）。更长的片子把 `tile` 改成 8×8，或者分段抽。

```bash
ffmpeg -v error -y -i /tmp/ref.mp4 -vf "fps=2,scale=180:-1,tile=8x4" -frames:v 1 /tmp/sheet.png
```

关键时刻抽原尺寸帧，量位置和字号：

```bash
ffmpeg -v error -y -ss 3.5 -i /tmp/ref.mp4 -frames:v 1 /tmp/ref-3.5.png
```

## 4. 声音

先画波形图找重音卡点：

```bash
ffmpeg -v error -y -i /tmp/ref.mp4 -filter_complex "showwavespic=s=1600x240" -frames:v 1 /tmp/wave.png
```

画面切换点可以用场景检测找。连续动效的片子切点不明显，阈值要降到 0.1–0.15：

```bash
ffmpeg -i /tmp/ref.mp4 -vf "select='gt(scene,0.15)',showinfo" -f null - 2>&1 | grep -o "pts_time:[0-9.]*"
```

## 5. 写拆解笔记

给用户的拆解笔记要包括：

- **结构：** 分几段，每段几秒，钩子在第几秒出现。
- **版式：** 背景、网格、字号层级、留白，内容从 y 多少开始。
- **配色：** 主色、强调色，标错和完成各用什么颜色。
- **动效语言：** 字怎么出现、标记怎么出现、元素怎么离场，转场是硬切、变形还是推移。
- **音效：** 打字声的密度，每类动作配什么声音，哪里留了静音。
- **可借鉴的点 / 不适合我们的点：** 各列 3 条。

做完拆解笔记再写分镜。
