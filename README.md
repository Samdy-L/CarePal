# CarePal 康伴 · 帕金森病智能康复伴侣系统

面向帕金森病患者的多模态康复伴侣系统。前端提供 AI 对话、用药日程、周度康复问卷、OCR 药盒识别、跌倒风险监控与用户中心；`CarePal-yolo/` 提供基于姿态估计的跌倒检测服务。

> **模型权重未包含在本仓库中**（单个文件超过 GitHub 100MB 限制），详见「运行」一节。

## 技术栈

| 模块 | 技术 |
|---|---|
| 前端 | uni-app、Vue3、Varlet、Vite |
| 跌倒检测服务 | Python、Ultralytics YOLO（姿态估计）、STGCN |
| 后端 | 独立的 HTTP 服务，不在本仓库内 |

## 本人负责

前端全部开发（`src/`、`vite.config.js`、`run.ps1`、`package.json`）：

- 基于 uni-app + Vue3 + Varlet + Vite 搭建跨端前端工程，采用「单页多模块」结构承载对话、日程表、周报告、OCR 识别、跌倒监控与用户中心
- 设计统一鉴权与请求封装（`uni.request` + Bearer Token + 401 掉线重登）；文件上传按运行环境分流（小程序端 `uni.uploadFile`、H5 端 `fetch` + `FormData`）
- 实现语音交互双通道回退：运行时能力检测优先使用 `MediaRecorder`，不支持时回退 `uni.getRecorderManager`
- 实现 OCR 拍照与相册双来源，并配置 5 分钟请求超时
- 负责前后端联调：以统一配置文件管理后端与跌倒检测服务两套地址，开发环境经 Vite 代理转发 `/api` 与 `/yoloapi` 以规避浏览器跨域预检 405，生产环境直连
- 编写 PowerShell 一键启动脚本，自动拉起前后端并在退出时递归回收进程树

> 本仓库还一并存档了 `CarePal-yolo/` 跌倒检测服务，便于完整运行。

## 前端结构

单页多模块（SPA）结构，全部业务模块承载于 `src/pages/index/index.vue`，由 `src/config/app.config.js` 的 `moduleList` 驱动：

| 模块 | key | 说明 |
|---|---|---|
| 对话 | `chat` | 文本 / 语音与 AI 对话 |
| 日程表 | `schedule` | 今日用药与训练安排 |
| 周报告 | `weekly-report` | 周度问卷与康复总结 |
| OCR 识别 | `ocr` | 拍照识别药盒与说明书 |
| 我的 | `profile` | 账号与提醒偏好 |

```
├── index.html
├── package.json              # uni-app 工程配置（Vue3 / Varlet / Vite）
├── vite.config.js            # 开发代理：/api → 后端，/yoloapi → 跌倒检测服务
├── run.ps1                   # 一键启动前后端，退出时递归回收进程树
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── pages.json
│   ├── manifest.json
│   ├── uni.scss
│   ├── config/app.config.js  # 后端地址、接口路径、录音 / OCR / 问卷等配置
│   └── pages/index/index.vue # 主页面（业务模块全量实现）
├── static/                   # 图标与图片
├── sound/ding.mp3
└── CarePal-yolo/             # 跌倒检测服务
    ├── api_server.py         # HTTP 服务入口
    ├── pipeline.py           # 推理流水线
    ├── yolo.py               # YOLO 姿态提取
    ├── STGCN.py              # 时序图卷积分类网络
    ├── train_stgcn.py        # 训练脚本
    ├── FallDetection.py
    ├── session_manager.py
    ├── config/               # 模型与推理参数
    └── models/               # 权重目录（.gitignore 已排除）
```

## 接口对接

前端通过 `src/config/app.config.js` 统一管理两套服务地址，开发环境走 Vite 代理、生产环境直连：

| 前缀 | 目标 | 用途 |
|---|---|---|
| `/api` | 后端服务（默认 `:8000`） | 登录注册、对话、OCR |
| `/yoloapi` | 跌倒检测服务（默认 `:8010`） | 视频帧跌倒检测 |

已使用的接口：`/auth/login`、`/auth/register`、`/chat/text`、`/chat/voice`、`/ocr/analyze`、`/detect/frame`。

- 请求统一走 `uni.request` 封装，带 Bearer Token 与 401 掉线处理。
- 文件上传在小程序端走 `uni.uploadFile`，在 H5 端走 `fetch` + `FormData`。
- 录音在支持 `MediaRecorder` 的环境使用浏览器接口，否则回退到 `uni.getRecorderManager`。

## 运行

1. 安装前端依赖：

   ```bash
   npm install
   ```

2. 准备跌倒检测模型权重（**未包含在本仓库**，需要自行获取或训练），放入：

   ```
   CarePal-yolo/models/best_model.pth
   CarePal-yolo/models/yolo26x-pose.pt
   ```

   训练入口见 `CarePal-yolo/train_stgcn.py`，参数见 `CarePal-yolo/config/models.json`。

3. 一键启动前后端（自动打开浏览器，退出时回收进程）：

   ```powershell
   .\run.ps1
   ```

   或分别启动：

   ```bash
   npm run dev:h5                        # 前端，默认 http://localhost:5173
   python .\CarePal-yolo\api_server.py   # 跌倒检测服务，默认 :8010
   ```

   后端地址在 `src/config/app.config.js` 的 `BACKEND_SERVER` 中修改。

## 构建

```bash
npm run build:h5          # Web 端
npm run build:mp-weixin   # 微信小程序端
```

构建产物输出到 `dist/`。
