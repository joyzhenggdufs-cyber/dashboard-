# Hermes 项目工作台

全景可视化面板，展示 Hermes 所有自动化项目的运行状态 + Obsidian 知识框架。

## 结构

```
hermes-workbench/
├── dashboard.html    # 主面板（暖陶风、响应式、PWA）
├── manifest.json     # PWA 清单（可安装到手机主屏幕）
├── sw.js            # Service Worker（离线缓存）
├── refresh.py       # 数据刷新脚本（拉 cron 状态 + Obsidian 统计）
├── data.json        # 刷新脚本输出的实时数据
└── README.md
```

## 运行

```bash
# 手动刷新数据
python3 refresh.py

# 打开面板
open dashboard.html
```

## 部署

推到 GitHub Pages 后，手机/Pad/Mac 浏览器都能访问。
