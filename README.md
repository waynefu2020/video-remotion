# Product Motion Video Skill

把一句产品卖点交给 AI，得到一条可以发布的 9:16 竖屏动效短视频。

这不是一段提示词，也不是视频教程。Skill 自带可运行的画面与声音底座、品牌素材、工程生成器、自动检查和三个真实案例。AI 会依次完成：

**创意 → 逐秒分镜 → 等你确认 → 制作 → 自检 → 第一版 → 修改 → 成片与封面**

## 适合做什么

- 产品功能演示
- 小红书、抖音竖屏短视频
- 文字动画、UI 动效、卡片、待办、日历、记忆与文件问答
- 无人声、由音乐和动作音效推动节奏的品牌短片

已有案例：

| 成片 | 核心变化 | 文件 |
| --- | --- | --- |
| 说话乱七八糟，日程井井有条 | 混乱口语 → 待办 → 日历 | [`ideashell-schedule.mp4`](ideashell-video/dist/ideashell-schedule.mp4) |
| 你忘了的，它都记得 | 问题 → 搜索记忆 → 带来源回答 | [`ideashell-memory.mp4`](ideashell-video/dist/ideashell-memory.mp4) |
| 帮你记，一起想 | 随口记录 → 回忆 → 行动 | [`ideashell-promo.mp4`](ideashell-video/dist/ideashell-promo.mp4) |

## 运营同事最快开始

打开已经装好本 Skill 的 Agent，复制下面这句话：

> 使用 product-motion-video Skill，帮我做一条 15 秒的小红书竖屏视频。主题是「开会不用记笔记，会后自动出纪要」。不要配音。先给我分镜，我确认后再制作。

AI 第一次应该只给你创意和逐秒分镜，不应该马上开始做。分镜确认后回复：

> 分镜可以，开始制作。

第一版出来后，用这个格式提修改：

> 第几秒 + 哪个东西 + 想改成什么样。

例如：

> 第 4–6 秒的三张卡片太慢了，间隔缩短一点，一张接一张出来；其他部分不动。

完整的非技术上手说明见：

**[运营人员使用手册](docs/training/operator-handbook.md)**

讲师授课用：

**[90 分钟内部培训讲师稿](docs/training/ideashell-video-workshop.md)**

## 重要：什么样的 AI 才能使用

模型名称不是唯一条件。Agent 还必须能够：

- 读取和写入文件
- 运行 Python 与 ffmpeg 命令
- 打开图片进行检查
- 把生成的 MP4 交给你

推荐使用：

1. **Cursor**：打开整个仓库，在 Agent 模式中使用。
2. **Grok bot**：上传 `.skill` 文件或连接本仓库，在可执行代码的工作区中使用。
3. **Claude 桌面端**：连接本地项目，并开启文件读写和命令执行能力后使用。

其他 Agent 也可以，但必须具备上面的执行能力。只有文字聊天能力、不能运行命令的普通聊天窗口不能独立生成成片。

## 安装

完整 Skill 在 [`product-motion-video/`](product-motion-video/)，入口是
[`product-motion-video/SKILL.md`](product-motion-video/SKILL.md)。

可直接上传或分发的单文件包：

[`dist/product-motion-video.skill`](dist/product-motion-video.skill)

### Cursor

本仓库已经在 `.cursor/skills/` 配好入口。用 Cursor 打开整个仓库，直接对 Agent 说“使用 product-motion-video Skill”即可。

### Grok bot

把 `product-motion-video.skill` 上传给 Grok bot，在可执行代码的工作区中说：

> 先读取这个 Skill。接下来严格按它的流程制作视频，在我确认分镜前不要开始渲染。

如果平台不接受 `.skill` 文件，就上传整个 `product-motion-video/` 目录。

### Claude 桌面端

让 Claude 桌面端连接本地项目，并确保它可以读写文件、运行 Python 和 ffmpeg。打开本仓库后，根目录的 `CLAUDE.md` 会把 Claude 指向同一份 Skill。

## Skill 里有什么

```text
product-motion-video/
├── SKILL.md                 完整执行流程
├── scripts/
│   ├── init_project.py      在空目录创建可运行的视频工程
│   ├── verify_video.py      检查尺寸、帧率、音轨、响度和黑边
│   ├── contact_sheet.py     生成联系表供审片
│   └── package_skill.py     重新打包 .skill 文件
├── starter/                 动画、音频、模板和品牌素材
├── references/              创意、制作与验收规范
└── examples/                三条已验证案例的结构总结
```

`ideashell-video/` 保存三个案例的完整源代码与成片，供 Agent 复用，不要求运营人员阅读。

## 已验证

打包后的 `.skill` 已经在全新空目录中完成端到端测试：

- 自动创建工程
- 导出 1080×1920、30fps MP4
- 生成音乐和音效
- 测得 -14.5 LUFS
- 检查四边无黑边
- 生成完整联系表

## 不做什么

- 不读取社交帖子的作者、点赞和评论
- 不复制参考视频的文案和品牌
- 不在分镜确认前开始制作
- 不把模板片当作新片交付
- 不让运营人员处理代码、字体或渲染报错
