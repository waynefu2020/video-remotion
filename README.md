# 闪念贝壳竖屏动效视频

这个仓库只做一种事：用代码做竖屏产品短视频。样子就像「说话乱七八糟，日程井井有条」那条：一个字一格打出来，口头禅标红后被吹走，剩下的字飞进待办，再排进日历，最后落到品牌结尾。

不做读链接、拆文案、看点赞评论。

做新片子按 [ideashell-video/PLAYBOOK.md](ideashell-video/PLAYBOOK.md)。Cursor、Grok、Claude（Opus 5.5）用的是同一份手册。同事培训讲义在 [docs/training/ideashell-video-workshop.md](docs/training/ideashell-video-workshop.md)。

已有成片在 `ideashell-video/dist/`：

- `ideashell-schedule.mp4`：28 秒，稿纸方格 → 待办 → 日历
- `ideashell-promo.mp4`：30 秒宣传片
- `ideashell-memory.mp4`：32 秒记忆能力

```bash
cd ideashell-video
python3 new_video.py todo_demo "随口一说，自动排好"
./build_todo_demo.sh
```
