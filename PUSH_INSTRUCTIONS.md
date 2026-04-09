# OfficeMind - DevDoc Generator Skill 推送指南

## 📊 本地提交状态

**仓库**: https://github.com/RussellCooper-DJZ/OfficeMind-New  
**本地领先远程**: 2 commits ahead

### 已提交的 commits

1. **ebd74b4** - feat: add DevDoc Generator Skill v3.0.0 as external skill
   - 添加 10 个文件
   - 3,125 行新增内容
   
2. **a59f412** - docs: add SKILL.md documentation
   - 193 行新增内容

---

## 🚀 推送步骤

### **方式 1: 使用 GitHub Personal Access Token**

1. **生成 Token**
   - 访问：https://github.com/settings/tokens/new
   - 选择 `classic` token
   - 勾选权限：`repo`
   - 生成并复制 token

2. **推送代码**
   ```bash
   cd /home/xsuper/.openclaw/workspace/OfficeMind-New
   git push https://<TOKEN>@github.com/RussellCooper-DJZ/OfficeMind-New.git main
   ```

### **方式 2: 使用 SSH (如果已配置)**

```bash
cd /home/xsuper/.openclaw/workspace/OfficeMind-New
git push origin main
```

---

## ✅ 推送后验证

推送完成后，访问：
https://github.com/RussellCooper-DJZ/OfficeMind-New/tree/main/skills/dev-doc-generator

应该能看到以下文件：
- ✅ index.js (15,672 bytes)
- ✅ SKILL.md (4,628 bytes)
- ✅ package.json
- ✅ package-lock.json
- ✅ .gitignore
- ✅ src/ 目录
- ✅ src/pro/ 子目录结构

---

## 🔧 使用方式

### **自动分析模式**
```bash
cd /home/xsuper/.openclaw/workspace/OfficeMind-New
node skills/dev-doc-generator/index.js --mode auto "CRM 系统" "客户信息管理和销售流程"
```

### **启发式问答模式**
```bash
cd /home/xsuper/.openclaw/workspace/OfficeMind-New  
node skills/dev-doc-generator/index.js --mode discovery "CRM 系统"
```

---

## 📝 技能说明

**DevDoc Generator Skill v3.0.0** 是一个专业的 CLI 文档生成工具，集成在 OfficeMind 中作为外挂 Skill 使用。

**核心功能：**
1. ✅ 双模式需求分析（自动分析 / 启发式问答）
2. ✅ 生成 4 份专业文档（PRD、架构、详细设计、任务分解）
3. ✅ CLI 命令行调用，便于 AI 使用
4. ✅ 完整的 UI、调用方式、运行方式说明

**输出文件：**
- `项目名-prd.md` - 产品需求文档
- `项目名-arch.md` - 技术架构设计
- `项目名-detail.md` - 详细设计文档  
- `项目名-tasks.md` - 任务分解文档

---

## 🎯 下一步

推送完成后，可以在 OfficeMind 中集成和测试该技能。如有问题，请参考 SKILL.md 文档。
