# 🎨 Agent 前端页面分类速查

| 类别 | 项目 | 一句话简介 (核心功能与亮点) | 技术栈 | 适合人群 |
| :--- | :--- | :--- | :--- | :--- |
| **🖼️ 纯前端/UI库** | **AgentX UI** | 专为 AIGC 应用设计的 React 组件库，提供构建 Agent 界面的各种“积木”。 | React, Antd, CSS-in-JS | React 开发者 |
| | **assistant-ui** | 一个用于构建 AI 聊天界面的 React 库，目标是让你能快速复刻出 ChatGPT 般的体验。 | React, TypeScript | React 开发者 |
| | **Agno UI** | 一个美观、开源的 Agent 交互界面，方便你与 Agent 聊天并查看其内部状态。 | 待核实 | 各类开发者 |
| | **agent-chat** | React 组件库，提供风格隔离的 AI 对话界面组件。 | React | React 开发者 |
| | **orcal-ui** | 面向多 Agent 系统的 React UI 组件集合。 | React | React 开发者 |
| | **Agentman Chat Widget** | 可轻松集成到任何网页中的、开箱即用的现代化聊天组件。 | 待核实 | 各类开发者 |
| **🚀 全栈平台/工具** | **Dify** | 功能强大的 LLM 应用开发平台，集成了可视化工作流、RAG、Agent 等，其前端基于 Next.js 构建，代码开源。 | Next.js, TypeScript, Python | 产品经理、全栈开发者 |
| | **LangFlow** | LangChain 的官方 GUI，通过拖拽连线的方式构建 AI 应用工作流。 | React, react-flow | 开发者、研究者 |
| | **LocalAGI** | 100% 本地运行的 AI Agent 平台，提供 Web UI 进行无代码的 Agent 配置与管理。 | Go, Docker | 注重隐私的开发者、爱好者 |
| | **OpenClaw** | 一个现象级的开源项目，能像“操作系统”一样直接操控你的电脑，拥有强大的社区生态。 | Node.js, TypeScript | 高级开发者、研究者 |
| | **Lobe Chat** | 一个现代化的 AI 聊天框架，支持多 AI 提供商、知识库和 MCP 市场。 | Next.js, TypeScript | 注重体验的开发者 |
| | **PageAgent** | 阿里巴巴开源的纯前端 GUI Agent 库，可直接在网页中运行并操作界面，无需后端。 | JavaScript, HTML | 前端开发者、产品经理 |
| | **Posse** | 为 Anthropic 托管 Agent 提供的开源 Web UI。 | 待核实 | 使用 Anthropic 服务的开发者 |
| | **Hera** | 一个基于 Claude Agent SDK 的自治 AI 平台，提供实时管理面板。 | 待核实 | 高级开发者 |
| | **Evo AI** | 一个用于创建和管理 AI Agent 的开源平台，包含可视化工作流编辑器。 | ReactFlow | 开发者 |
| **🎯 专用 Web Agent** | **LiteWebAgent** | 基于 VLM 的开源 Web Agent 套件，提供直观的浏览器界面，让 Agent 替你操作网页。 | Vercel, Chrome Extension | 开发者、研究者 |
| | **Magentic-UI (微软)** | 微软开源的“以人为本”的 Web Agent，强调人机协作，让你能实时监督 AI 的行动。 | AutoGen | 开发者、研究者 |
| | **MolmoWeb (Ai2)** | 艾伦AI研究所开源的视觉 Web Agent，可在此基础上开发你自己的网页自动化工具。 | 待核实 | 研究者、高级开发者 |
| | **UI-TARS (字节跳动)** | 字节跳动开源的 GUI Agent，支持自然语言指令操控界面。 | 待核实 | 开发者、研究者 |

### 🎯 如何选择适合你的参考项目？

*   **如果你想快速搭建或集成一个聊天界面**，**AgentX UI** 和 **assistant-ui** 这类纯 UI 库是最佳选择。
*   **如果你想了解完整的 Agent 应用架构**，**Dify** 和 **LocalAGI** 这样的全栈平台是很好的参考，它们开源了前端到后端的完整代码。
*   **如果你想构建一个能自动操作网页的 Agent**，可以重点关注 **LiteWebAgent**、**Magentic-UI** 这类专用 Web Agent，它们的设计理念和实现方式能提供很大启发。
*   **如果你更偏爱终端操作**，可以看看 **Claude Code** 这类通过命令行交互的 Agent，其终端 UI 的设计逻辑同样有参考价值。


为你的 Agent 挑选一个美观又趁手的“门面”，从下面的开源项目里挑，应该能找到心仪的那一个。

### 💡 方案概览：从组件到完整平台

| 方案 | 适用人群 | 优点 | 缺点 |
| :--- | :--- | :--- | :--- |
| **📦 组件库** | 追求高度定制的开发者 | 自由度高，可按需组合，深度集成到现有Vue项目。 | 需要一定的前端开发能力，所有模块都需要自己动手搭。 |
| **🚀 完整项目模板** | 想要快速上手的开发者 | 开箱即用，包含完整的前后端交互逻辑，可以快速看到效果。 | 灵活性相对较低，二次开发可能需要理解其代码结构。 |
| **🎨 全栈AI平台** | 需要一站式解决方案的团队 | 功能强大，通常集成了工作流、RAG、插件市场等，是一个完整的AI应用平台。 | 系统复杂，学习成本高，可能超出你当前“为Agent找个UI”的简单需求。 |

### 🧩 组件库 (Components)
* **ant-design-x-vue**：基于 Ant Design Vue，提供**开箱即用**的对话组件。核心功能包括**流式渲染**、**思维链可视化**、智能建议等，专业性强。
* **LiaoKit**：一款专为 AI 对话场景设计的现代化 Vue3 组件库，内置强大的**流式响应引擎**（支持打字机效果和 SSE），并提供了**多窗口管理**等企业级功能，适合构建复杂的 AI 应用。
* **@linloop/ai-chat-plugin**：功能强大的 Vue 3 聊天组件，支持**虚拟滚动**（适合大量消息）、**深度思考显示**、多模型切换和完整的主题定制。
* **Vue Bot UI**：基于 Vue.js 的组件库，提供了丰富的消息气泡和布局组件，支持通过CSS变量轻松定制主题，插件机制也让扩展功能变得方便。
* **uve-ai-chat**：支持 uni-app 的跨平台组件，一套代码可编译到H5、小程序、App，支持富文本和打字效果。
* **vue-ai-chat**：一个简单的 Vue.js AI 聊天组件，通过 npm 安装后，可以快速集成到 Vue 项目中，适合对功能要求不复杂的场景。

### 🚀 完整项目模板 (Templates)
* **@yaoqing-test/ai-chat**：基于 Vue3 + Vite + Naive UI 的现代化模板，功能完善，支持 Markdown 预览、Mermaid 图表、数学公式等。
* **ChatGPT-PerfectUI**：用 Vue3 + Vite + Tailwindcss 完美复刻 ChatGPT 的 Web App，视觉上1:1还原，如果你喜欢 ChatGPT 的界面风格，这个模板会很合适。
* **vue3-deepseek-webai**：Vite7.2 + Vue3.5 + Arco Design 构建，完美模仿 DeepSeek 官方 Web 体验，支持流式输出和双主题。
* **Zunder GPT Clone AI Starter**：基于 Nuxt 3 + Vue 3 + TailwindCSS 的 ChatGPT 克隆启动模板，适合需要 SEO 或服务端渲染的场景。
* **TerraMours ChatGPT**：基于 Vue3 + TS + Naive UI + Vite 的 ChatGPT 项目，集成了登录、多模型聊天和图片生成等功能，功能更完整。
* **uniapp+vue3+deepseek-chat**：使用 uni-app + Vue3 构建的跨三端 (H5, 小程序, App) AI 聊天应用，特别适合需要覆盖多平台的场景。

### 🎨 全栈AI平台 (Platforms)
* **MateChat**：华为开源的对话式 UI 组件库，面向企业级智能化场景，支持 DeepSeek、盘古、ChatGPT 等大模型，提供多种开箱即用的主题和业务场景组件。

### 💎 总结与建议
简单来说，可以根据你的需求来做选择：
*   **如果追求深度定制**，想在现有项目里集成一个漂亮的聊天窗口，可以选 **`ant-design-x-vue`** 或 **`LiaoKit`**。
*   **如果想快速看到效果**，不想从零搭架子，可以试试 **`@yaoqing-test/ai-chat`** 或 **`ChatGPT-PerfectUI`**。
*   **如果有跨平台需求**，需要同时覆盖网页、小程序和App，那么 **`uve-ai-chat`** 和 **`uniapp+vue3+deepseek-chat`** 会比较合适。

如果想了解更多关于某个项目的细节，或者需要我帮你评估一下哪个更适合你的具体场景，随时可以告诉我～