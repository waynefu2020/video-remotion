# Product Motion Video Skill

这是一个完整的视频制作 Skill，不是提示词或教程。把整个 `product-motion-video/` 目录交给能运行命令的 Agent，它可以：

1. 和运营确认主题、时长、参考和落版。
2. 先给创意与逐秒分镜，等确认。
3. 自动创建可运行的视频工程。
4. 制作文字、UI、卡片、日历、记忆等动效。
5. 生成音乐和动作音效。
6. 输出 MP4，自动检查尺寸、帧率、音轨、响度和黑边。
7. 生成联系表供人眼审片。
8. 按反馈修改，并交付两种封面。

## 使用

在 Agent 中说：

> 使用 product-motion-video Skill，帮我做一条 15 秒的小红书竖屏视频。主题是「开会不用记笔记，会后自动出纪要」。先给我分镜，确认后再制作。

运营人员不需要运行任何命令。

## 安装

- **Cursor：** 把目录复制到项目的 `.cursor/skills/product-motion-video/`。
- **Claude Code / Opus：** 把目录复制到支持的 Skills 目录，或让 Agent 直接读取本目录的 `SKILL.md`。
- **Grok 或其他 Agent：** 上传整个目录，要求先读 `SKILL.md`。

也可以生成一个便于上传的单文件包：

```bash
python3 scripts/package_skill.py
```

输出为仓库根目录下的 `dist/product-motion-video.skill`。

## Skill 自测

下面的测试会在空目录创建工程并生成 12 秒 MP4：

```bash
python3 scripts/init_project.py \
  --output /tmp/motion-video-test \
  --slug meeting_notes \
  --title "开会不用记笔记"

cd /tmp/motion-video-test
./build_meeting_notes.sh

python3 /path/to/product-motion-video/scripts/verify_video.py \
  dist/ideashell-meeting_notes.mp4
```

自动检查通过后，还必须打开联系表做人工审片。
