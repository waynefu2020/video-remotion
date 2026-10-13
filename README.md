# 镜析

把一条公开链接拆成作者、正文、互动和一份读片笔记。支持抖音、小红书、TikTok、Instagram、YouTube 和 X。

## 数据从哪来

- 抖音、小红书、TikTok、Instagram：你自己的 [TikHub](https://tikhub.io) 令牌。这四枚令牌按平台分开授权，不能互相借用。
- YouTube：[YouTube.js](https://github.com/LuanRT/YouTube.js)（`youtubei.js`）。不需要 API key，读的是公开视频信息，有字幕时会把口播摘出来。
- X：优先 [FxEmbed](https://github.com/FxEmbed/FxEmbed) 的状态接口（浏览、媒体、转推）。失败时改用 [react-tweet](https://github.com/vercel/react-tweet) 里的 syndication 接口。

令牌只放在服务端。页面拿不到。

## 本地运行

```bash
npm install
cp .env.example .env.local
# 把四个平台的 TikHub 令牌填进 .env.local
npm run dev
```

打开 [http://127.0.0.1:43123](http://127.0.0.1:43123)。

可以贴完整链接，也可以贴整段分享文案。`Ctrl/⌘ + Enter` 直接拆。

YouTube 和 X 的 TikHub 权限没开也能用。如果以后在后台勾上了这两个平台，把令牌写进 `TIKHUB_TOKEN_YOUTUBE` 和 `TIKHUB_TOKEN_X` 即可；当前读片仍以 GitHub 上的公开方案为准。
