# DevDoc Generator Skill

**版本**: 3.0.0  
**描述**: 专业 CLI 文档生成器 - DevDoc Generator Pro for OfficeMind

## 📋 功能概览

### **核心功能**

1. **双模式需求分析**
   - **自动生成模式**: 快速分析，1 分钟完成
   - **启发式问答模式**: 多轮对话引导，逐步明确需求

2. **4 份专业文档生成**
   - PRD 产品需求文档
   - 技术架构设计文档
   - 详细设计文档
   - 任务分解文档

3. **CLI 命令行调用**
   - 支持多种参数
   - 灵活的输出配置
   - 友好的交互界面

---

## 🚀 使用方式

### **方式 1: 自动分析模式**

```bash
node /home/xsuper/.openclaw/workspace/OfficeMind-New/skills/dev-doc-generator/index.js --mode auto "项目名称" "需求描述"
```

**示例:**
```bash
node /home/xsuper/.openclaw/workspace/OfficeMind-New/skills/dev-doc-generator/index.js --mode auto "CRM 系统" "客户信息管理和销售流程"
```

**特点:**
- ✅ 无需交互
- ✅ 快速生成
- ✅ 适合需求明确的项目

---

### **方式 2: 启发式问答模式**

```bash
node /home/xsuper/.openclaw/workspace/OfficeMind-New/skills/dev-doc-generator/index.js --mode discovery "项目名称"
```

**特点:**
- ✅ AI 引导式提问
- ✅ 通用问题 → 针对性问题
- ✅ 适合需求不明确的项目

---

### **方式 3: 自定义输出目录**

```bash
node /home/xsuper/.openclaw/workspace/OfficeMind-New/skills/dev-doc-generator/index.js --mode auto "项目名" --output ./custom-output
```

---

## 📝 命令行参数

| 参数 | 说明 | 默认值 |
|--|--|--|
| `--mode` | 运行模式：auto|discovery | auto |
| `--output` | 输出目录 | ./output |
| `-o` | 输出目录缩写 | ./output |
| `-i` | 交互模式 | false |

---

## 📊 生成的文档

### **1. PRD 产品需求文档 (`-prd.md`)**
- ✅ 项目信息
- ✅ 需求分类表
- ✅ MoSCoW 优先级
- ✅ 用户故事
- ✅ 验收标准

### **2. 技术架构设计 (`-arch.md`)**
- ✅ 系统架构图 (Mermaid)
- ✅ 四层架构设计
- ✅ 完整技术栈推荐
- ✅ 部署架构说明

### **3. 详细设计文档 (`-detail.md`)**
- ✅ TypeScript 接口定义
- ✅ PostgreSQL Schema
- ✅ 错误处理机制
- ✅ 代码规范说明

### **4. 任务分解 (`-tasks.md`)**
- ✅ 6 个开发阶段
- ✅ 58 个详细子任务
- ✅ 工时估算 (~280 小时)
- ✅ Mermaid 时间线图

---

## 🏗️ Skill 文件结构

```
OfficeMind-New/
└── skills/
    └── dev-doc-generator/
        ├── index.js              # 主程序入口
        ├── package.json          # 项目依赖
        ├── package-lock.json     # 依赖锁定
        ├── src/                  # 核心模块
        │   ├── index.js          # 模块入口
        │   ├── index-cli.js      # CLI 调用模块
        │   ├── index-auto.js     # 自动分析模块
        │   ├── index.js          # 核心生成器
        │   ├── pro/              # 增强版生成器
        │   │   ├── analyzers/    # 分析器
        │   │   │   └── requirement-analyzer.js
        │   │   ├── designers/    # 设计师
        │   │   │   ├── architecture-designer.js
        │   │   │   └── detailed-designer.js
        │   │   └── index.js
        │   └── doc-generator.js  # 文档生成器
        └── .gitignore            # Git 忽略文件
```

---

## 🎯 运行示例

### **示例 1: 自动生成**
```bash
$ node skills/dev-doc-generator/index.js --mode auto "在线文档系统" "需要用户认证、文档创建编辑、多人实时协作"

🚀 DevDoc Generator Skill v3.0.0
项目名称：在线文档系统
需求描述：需要用户认证、文档创建编辑、多人实时协作
分析模式：自动分析
输出目录：./output

📁 已创建输出目录：./output

📋 步骤 1/5: 需求分析...

✅ 需求分析完成!

📝 步骤 2/5: 生成 PRD 和架构设计...

📝 步骤 3/5: 生成详细设计...

📝 步骤 4/5: 生成任务分解...

✨ 完成!
输出目录：./output
文件列表:
- PRD 文档
- 架构设计
- 详细设计
- 任务清单
```

---

## 🔧 技术栈

- **语言**: Node.js 18+
- **格式**: CommonJS (require)
- **输出**: Markdown 格式
- **图表**: Mermaid.js
- **编码**: UTF-8

---

## 📚 相关文档

- **README.md**: 项目说明
- **SKILL.md**: 当前文档
- **USAGE_GUIDE.md**: 使用指南
- **DEMO.md**: 使用演示

---

---

> **版本**: v3.0.0  
> **维护**: DevDoc Team  
> **更新时间**: 2026-04-09
