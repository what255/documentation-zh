# 2024sms 静态页面爬取示例

该示例项目用于登录站点后抓取页面数据，并输出静态 HTML 页面与 JSON 数据（不使用数据库）。

> **提示**：部分站点会拦截无头/脚本访问，请优先使用 Cookie 登录方式，或在本地环境运行。

## 功能

- 支持 Cookie 或账号密码登录
- 可配置抓取页面列表
- 自动抽取页面表格数据（若无表格则保存文本摘要）
- 输出静态页面 `output/index.html` 与 `output/data.json`

## 目录结构

```
crawler_project/
├── crawler.py
├── requirements.txt
├── config.example.json
└── README.md
```

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

复制并编辑 `config.example.json`：

```json
{
  "base_url": "https://2024sms.com/",
  "login_url": "https://2024sms.com/login",
  "username": "async01",
  "password": "wzb2026966",
  "username_field": "username",
  "password_field": "password",
  "pages": [
    "/user",
    "/message/list"
  ]
}
```

> 说明：`login_url`、`username_field`、`password_field` 请根据登录表单实际字段调整。

## 运行

### 方式一：账号密码登录

```bash
python crawler.py --config config.json
```

### 方式二：使用 Cookie 登录（推荐）

```bash
python crawler.py --config config.json --cookie "key1=value1; key2=value2"
```

或传入 Cookie 文件：

```bash
python crawler.py --config config.json --cookie-file cookie.txt
```

### 输出

- `output/data.json`：抓取到的数据
- `output/index.html`：静态展示页面

## 常见问题

- **请求 403**：目标站点可能拦截脚本访问，可尝试在本地环境运行或使用有效 Cookie。
- **登录失败**：请确认登录接口地址和字段名，必要时抓包或查看页面表单结构。
