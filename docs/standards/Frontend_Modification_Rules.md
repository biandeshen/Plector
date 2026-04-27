# Plector 前端修改规范

> 版本: v1.0.0 | 最后更新: 2026-04-28
>
> 本文档是 CLAUDE.md 第三节的详细扩展版。

---

## 一、修改前必做

### 1.1 三步流程

```
步骤 1: Read 完整内容
步骤 2: git log 分析历史
步骤 3: 修改代码
步骤 4: 验证修改
```

### 1.2 步骤详解

#### 步骤 1: Read 完整内容

**为什么**：避免遗漏重要逻辑、样式、依赖

**要求**：
- 读取完整文件，不要只读部分
- 对于 Vue 组件，列出 props/emits/computed
- 理解组件的数据流和事件流

#### 步骤 2: git log 分析历史

```bash
git log -p -3 -- <file>
```

**为什么**：避免重复已知问题

**分析内容**：
- 最近 3 次修改记录
- 修改原因和修复方案
- 是否有相关的 bug 历史

#### 步骤 3: 修改代码

根据场景选择合适的修改策略（见第二节）

#### 步骤 4: 验证修改

- 运行 `pytest` 或 `python scripts/validate_skills.py`
- 前端可用 `chrome-devtools` MCP 截图对比

---

## 二、修改策略矩阵

### 2.1 场景分类

| 场景 | 特征 | 策略 | 工具 |
|------|------|------|------|
| 修改样式 | 只改 CSS | 只改 CSS，不动 HTML/JS | `Edit` |
| 添加功能 | 扩展现有组件 | 追加不改原有 | `Edit` |
| 修复 bug | 修复问题 | 只改问题行 | `Edit` |
| 修改 Vue 组件 | 需要理解组件结构 | 先列 props/emits/computed | `Read` + `Grep` |
| 重写页面 | 大范围改动 | **需用户明确授权** | `Write` |

### 2.2 样式修改（CSS）

**原则**：只改 CSS，不动 HTML/JS

```vue
<!-- ❌ 错误：同时改了 HTML 和 CSS -->
<template>
  <div class="old-class">...</div>  <!-- HTML 改变 -->
</template>
<style>
.old-class { color: red; }  <!-- 样式改变 -->
</style>

<!-- ✅ 正确：只改 CSS -->
<style>
.old-class { color: blue; }  <!-- 只改样式 -->
</style>
```

### 2.3 添加功能

**原则**：追加不改原有

```vue
<!-- ✅ 正确：在现有结构上追加 -->
<template>
  <div class="container">
    <div class="existing">...</div>  <!-- 不动 -->
    <div class="new-feature">...</div>  <!-- 新增 -->
  </div>
</template>
```

### 2.4 修复 Bug

**原则**：只改问题行

```vue
<!-- ✅ 正确：精确定位问题 -->
<script>
// 问题：缺少 await
async function handleClick() {
-   await fetchData()  // 原来没有 await
+   await fetchData()  // 添加 await
}
</script>
```

### 2.5 Vue 组件修改

**原则**：先列结构再修改

```markdown
## 修改 Vue 组件前分析清单

### 1. Props（输入）
- [ ] 列出所有 props 名称和类型
- [ ] 理解每个 prop 的用途

### 2. Emits（输出）
- [ ] 列出所有 emit 事件名称和参数
- [ ] 理解触发时机

### 3. Computed（计算属性）
- [ ] 列出所有 computed
- [ ] 理解依赖关系

### 4. Data（响应式数据）
- [ ] 列出所有 data
- [ ] 理解初始化逻辑

### 5. Methods（方法）
- [ ] 列出所有方法
- [ ] 理解调用关系

### 6. 生命周期
- [ ] 确认涉及的钩子（mounted/updated 等）
```

### 2.6 重写页面

**原则**：需要用户明确授权

```markdown
## 重写页面申请

需要重写：[组件名称]

**原因**：
[为什么需要重写]

**影响范围**：
- 受影响组件：[列出]
- 受影响页面：[列出]

**建议方案**：
[简述重写方案]

请确认是否授权重写？
```

---

## 三、防退化流水线

### 3.1 流水线概述

```
[修改前] → [Read + Git Log] → [修改] → [验证] → [完成]
              ↓                  ↓         ↓
          分析历史            遵循策略    pytest/截图
```

### 3.2 关键检查点

| 阶段 | 检查点 | 说明 |
|------|--------|------|
| 修改前 | Read 完整内容 | 确保理解上下文 |
| 修改前 | Git Log 分析 | 避免已知问题 |
| 修改中 | 遵循策略 | 根据场景选择正确策略 |
| 修改后 | 运行验证 | pytest 或截图对比 |

---

## 四、组件修改进阶

### 4.1 Props 和 Emits

```vue
<script>
export default {
  props: {
    // 分析清单
    title: String,        // [ ] 用途：组件标题
    items: Array,          // [ ] 用途：列表数据
    loading: Boolean      // [ ] 用途：加载状态
  },
  emits: [
    // 分析清单
    'select',             // [ ] 时机：选择列表项时
    'update:items'       // [ ] 时机：列表数据更新时
  ]
}
</script>
```

### 4.2 Computed 依赖

```vue
<script>
computed: {
  // 分析清单
  filteredItems() {
    // [ ] 依赖：this.items, this.search
    // [ ] 用途：过滤后的列表
    return this.items.filter(item =>
      item.name.includes(this.search)
    )
  },
  isEmpty() {
    // [ ] 依赖：this.filteredItems
    // [ ] 用途：判断是否为空
    return this.filteredItems.length === 0
  }
}
</script>
```

### 4.3 事件处理

```vue
<script>
methods: {
  // 分析清单
  handleSelect(item) {
    // [ ] 触发 emit：'select'
    // [ ] 参数：item 对象
    this.$emit('select', item)
  },
  handleInput(e) {
    // [ ] 触发 emit：'update:items'
    // [ ] 参数：e.target.value
    this.$emit('update:items', e.target.value)
  }
}
</script>
```

---

## 五、样式修改规范

### 5.1 样式优先级

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 内联 `style=""` | 最高优先级，不推荐 |
| 2 | 组件 `<style>` | 当前组件样式 |
| 3 | 全局 CSS | 全局生效 |
| 4 | Tailwind 类 | 如果使用 Tailwind |

### 5.2 样式规范

```css
/* ✅ 正确：使用语义化类名 */
.container { ... }
.header-title { ... }
.list-item { ... }

/* ❌ 错误：使用位置相关类名 */
.left-box { ... }
.big-red-button { ... }
```

### 5.3 响应式设计

```css
/* 移动优先 */
.container {
  padding: 16px;  /* 移动端 */
}

@media (min-width: 768px) {
  .container {
    padding: 32px;  /* 平板 */
  }
}

@media (min-width: 1024px) {
  .container {
    padding: 48px;  /* 桌面 */
  }
}
```

---

## 六、修改验证方法

### 6.1 后端验证

```bash
# 运行 pytest
python -m pytest

# 运行技能验证
python scripts/validate_skills.py

# 运行代码检查
ruff check core/ skills/ channels/
```

### 6.2 前端验证（截图对比）

```bash
# 使用 chrome-devtools MCP
# 1. 打开浏览器到当前页面
# 2. 截图保存为 baseline.png
# 3. 修改代码
# 4. 截图保存为 current.png
# 5. 对比两张截图
```

### 6.3 热重载验证

```bash
# 启动开发服务器
npm run dev

# 修改代码后，检查页面是否自动更新
# 如果没有更新，检查是否有缓存问题
```

---

## 七、常见问题

### Q1: 修改后样式乱了怎么办？

```bash
# 1. 检查是否不小心修改了 HTML 结构
git diff <file>

# 2. 如果是样式问题，检查是否有拼写错误
# 3. 清除浏览器缓存
# 4. 检查是否有全局样式冲突
```

### Q2: Vue 组件报错怎么办？

```vue
<!-- 常见错误 1：prop 类型不匹配 -->
<!-- ❌ 错误：传入字符串期望数字 -->
<ChildComponent :count="'5'" />
<!-- ✅ 正确：直接传入数字 -->
<ChildComponent :count="5" />

<!-- 常见错误 2：emit 参数错误 -->
<!-- ❌ 错误：emit 名称拼写错误 -->
this.$emit('click', item)  // 应该是 'select'
```

### Q3: 修改导致其他功能失效？

```markdown
## 排查步骤

1. [ ] 回滚修改，检查功能是否恢复
2. [ ] 逐步恢复修改，定位问题代码
3. [ ] 检查是否有依赖关系被破坏
4. [ ] 查看 git log，是否有相关修改历史
```

---

## 八、检查清单

### 修改前
- [ ] Read 完整文件内容
- [ ] git log 分析最近修改历史
- [ ] 列出 Vue 组件的 props/emits/computed
- [ ] 理解数据流和事件流

### 修改中
- [ ] 遵循场景对应的修改策略
- [ ] 不破坏现有功能
- [ ] 不引入新的问题

### 修改后
- [ ] 运行 pytest 验证
- [ ] 运行技能验证脚本
- [ ] 截图对比（如有 UI 变更）
- [ ] 测试相关功能

---

## 九、版本历史

- v1.0.0 (2026-04-28)：初始版本
