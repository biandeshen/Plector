# Claude Code 联网能力方案

> **创建时间**: 2026-04-18
> **序号**: 86
> **标签**: claude-code, mcp, 联网, fetch, web-search, browser-automation
> **状态**: 已实施
> **安装日期**: 2026-04-19

---

## 核心需求

让 Claude Code 能够访问互联网，获取实时信息、抓取网页内容、操控浏览器等。

---

## 方案对比

| 方案 | 工具 | 适用场景 | 一句话总结 |
|------|------|----------|-----------|
| **方案一** | 官方内置 Web Search | 需要最新资讯、查资料 | 快问快答，信息检索 |
| **方案二** | Fetch MCP | 分析指定的网页 | 指哪打哪，内容提取 |
| **方案三** | Browser Automation MCP | 需要与网页交互、自动化测试 | 人机合一，模拟操作 |
| **方案四** | AI Agent MCP | 复杂的、多步骤的研究任务 | 委派任务，自主完成 |

---

## 方案一：官方内置 Web Search

### 工作原理
- 让 Claude 主动发起网络搜索，抓取实时信息
- 支持多级搜索，根据首次结果优化查询词
- 所有引用信息都会提供来源

### 主要用途
- 获取最新的 API 文档
- 技术动态查询
- 排查依赖过时信息的问题

---

## 方案二：通用型 Fetch MCP

### 工作原理
- 网页下载器，直接访问指定的 URL
- 抓取页面的完整 HTML 或纯文本内容
- 擅长精确提取，不适合广撒网式搜索

### 安装命令

```bash
# 方式一：使用 npx（推荐）
claude mcp add fetch -- npx -y @modelcontextprotocol/server-fetch

# 方式二：本地安装
claude mcp add fetch node ~/.claude-custom-mcp/fetch-mcp/dist/index.js --scope user
```

### 使用示例

```
Fetch the content of https://react.dev/learn and summarize the main points for me.
```

### 主要用途
- 总结、翻译或分析已知网址的网页内容
- 技术文档获取
- 离线阅读内容保存

---

## 方案三：全能型浏览器自动化 MCP

### 核心原理
- 通过 MCP 协议连接 Playwright 或 Puppeteer
- 让 Claude 拥有控制浏览器的"手脚"

### 代表性方案

| 工具 | 特点 |
|------|------|
| **Browser Use** | 支持本地和远程浏览器，可用于自动化操作 |
| **mare-browser-mcp** | 精简的 Chromium 控制能力，无需 Playwright API |
| **Blueprint MCP for Firefox** | 直接控制真实 Firefox，可利用已有登录状态 |

### 主要用途

1. **自动化网页交互**
   - 登录、填表、提交等重复性任务
   - 批量操作

2. **网页数据抓取与分析**
   - 自动抓取多个页面数据
   - 进行分析和总结

3. **UI 自动化测试**
   - 根据指令自动测试 Web 应用

---

## 方案四：AI Agent MCP

### 代表项目
- **BrowserCat MCP**

### 工作原理
- 本身就是一个智能代理
- 接收高层指令（如"搜索AI新闻并总结成报告"）
- 自主规划、执行一系列搜索、浏览和提取操作
- 支持云端部署，多人协作

### 主要用途

1. **市场调研**
   - 自动收集、整理、分析竞争对手信息

2. **内容聚合**
   - 根据主题从多个网站抓取内容并生成简报

3. **复杂研究**
   - 多轮搜索和交叉验证的深度研究

---

## 推荐选择

| 场景 | 推荐方案 |
|------|----------|
| **日常使用** | Fetch MCP |
| **需要"货比三家"** | Web Search |
| **自动化填表/测试** | Browser Automation MCP |
| **复杂多步研究** | AI Agent MCP |

### 最佳实践

从 **Fetch MCP** 开始，满足大部分需求。日常工作中，它能帮你：
- 获取技术文档
- 分析指定网页内容
- 提取关键信息

需要更复杂能力时，再启用其他方案。

---

## 安装记录

| 日期 | 安装内容 | 状态 |
|------|----------|------|
| 2026-04-19 | `mcp-fetch-server` | ✅ Connected |

### 安装命令

```bash
claude mcp add fetch -- npx -y mcp-fetch-server
```

### MCP 服务器列表

```
thinking:       ✓ Connected (npx @modelcontextprotocol/server-sequential-thinking)
code-reasoning: ✓ Connected (npx @mettamatt/code-reasoning)
openspace:      ✓ Connected (openspace-mcp)
chrome-devtools: ✓ Connected (npx -y chrome-devtools-mcp@latest)
fetch:          ✓ Connected (npx -y mcp-fetch-server)
```

---

## 相关文档

- [[84_AI助手_核心框架参考]] - AI助手框架参考
- [[85_Claude_Code_自审查方案]] - Claude Code 自审查方案
- [[66_规范_技能开发规范]] - 技能开发规范
