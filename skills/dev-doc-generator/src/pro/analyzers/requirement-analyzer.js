/**
 * Requirement Analyzer - 专业的需求分析模块
 * 
 * 功能：
 * 1. 需求收集与解析
 * 2. 需求分类与归类
 * 3. 优先级排序 (MoSCoW)
 * 4. 用户故事编写
 * 5. 验收标准定义
 */

export class RequirementAnalyzer {
  constructor(initialRequirements) {
    this.initialRequirements = initialRequirements;
    this.requirements = [];
    this.categorized = {};
  }

  async analyze() {
    // Step 1: 需求解析
    const parsed = this.parseRequirements();
    
    // Step 2: 需求分类
    const categorized = this.categorizeRequirements(parsed);
    
    // Step 3: 优先级分析
    const priorities = this.assignPriorities(categorized);
    
    // Step 4: 用户故事提取
    const userStories = this.extractUserStories(parsed);
    
    // Step 5: 验收标准生成
    const acceptanceCriteria = this.generateAcceptanceCriteria(categorized);
    
    return {
      originalRequirement: this.initialRequirements,
      parsedRequirements: parsed,
      categoryMatrix: categorized,
      priorityPriorities: priorities,
      userStories: userStories,
      acceptanceCriteria: acceptanceCriteria
    };
  }

  parseRequirements() {
    // 文本解析 - 识别关键信息
    const textLower = this.initialRequirements.toLowerCase();
    
    const features = [];
    const nfrs = [];
    
    // 功能需求识别
    const featureKeywords = [
      '创建', '删除', '修改', '更新', '搜索', '查询', '上传', '下载',
      '登录', '注册', '管理', '共享', '协作', '编辑', '审核', '审批',
      '支付', '订购', '配送', '通知', '提醒', '分享', '导出', '导入'
    ];
    
    const nonFunctionalKeywords = [
      '性能', '安全', '加密', '速度', '并发', '可靠', '稳定',
      '兼容', '响应', '加载', '缓存', '备份', '恢复', '审计', '日志'
    ];
    
    features.push(...this.extractFeatures(textLower, featureKeywords));
    nfrs.push(...this.extractNFRs(textLower, nonFunctionalKeywords));
    
    return {
      features,
      nfrs,
      complexity: this.assessComplexity(textLower),
      stakeholders: this.identifyStakeholders(textLower)
    };
  }

  categorizeRequirements(parsed) {
    const categories = {
      authentication: [],
      core: [],
      communication: [],
      data: [],
      admin: [],
      integrations: []
    };
    
    const keywordMapping = {
      authentication: ['登录', '注册', '认证', '授权', '密码', 'token', 'JWT'],
      core: ['创建', '删除', '修改', '搜索', '查询', '详情'],
      communication: ['聊天', '消息', '通知', '提醒', '邮件', '分享'],
      data: ['上传', '下载', '文件', '图片', '存储', '数据库'],
      admin: ['管理员', '权限', '角色', '审核', '日志', '配置'],
      integrations: ['支付', '第三方', 'API', '集成', 'webhook', 'SSO']
    };
    
    for (const category in keywordMapping) {
      for (const req of parsed.features) {
        if (keywordMapping[category].some(k => req.toLowerCase().includes(k))) {
          categories[category].push(req);
        }
      }
    }
    
    // Fill in NFRs
    if (parsed.nfrs.length > 0) {
      categories.performance = parsed.nfrs;
    }
    
    return {
      classification: categories,
      coverage: this.calculateCoverage(categories),
      potentialGaps: this.identifyGaps(categories)
    };
  }

  assignPriorities(categorized) {
    const priorities = {
      mustHave: [],
      shouldHave: [],
      couldHave: [],
      wontHave: []
    };
    
    // 根据业务逻辑分配优先级
    for (const [category, items] of Object.entries(categorized.classification)) {
      for (let i = 0; i < items.length; i++) {
        const item = items[i].split(',')[0].trim();
        
        if (category === 'authentication' || category === 'core') {
          if (i === 0) {
            priorities.mustHave.push(item + ' (核心功能)');
          } else {
            priorities.shouldHave.push(item);
          }
        } else if (category === 'admin' || category === 'integrations') {
          priorities.couldHave.push(item);
        }
      }
    }
    
    return priorities;
  }

  extractUserStories(parsed) {
    const stories = [];
    
    const templates = [
      '作为 <user>，我想要 <feature>，以便于 <benefit>'
    ];
    
    for (const feature of parsed.features.slice(0, 5)) {
      stories.push(this.formatUserStory(feature));
    }
    
    return stories;
  }

  generateAcceptanceCriteria(categoryMatrix) {
    const criteria = [];
    
    for (const [category, items] of Object.entries(categoryMatrix.classification)) {
      for (const item of items.slice(0, 2)) {
        criteria.push({
          requirement: item,
          category: category,
          type: '功能验收',
          description: `验收 ${item} 功能的可用性、完整性和正确性`
        });
      }
    }
    
    // Add NFR criteria
    if (categoryMatrix.classification.performance?.length > 0) {
      criteria.push({
        requirement: '性能指标',
        category: '非功能性',
        type: '性能验收',
        description: '系统响应时间 < 500ms，并发用户支持 > 100'
      });
    }
    
    return criteria;
  }

  formatUserStories(stories) {
    return stories.map(story => `- **${story.title}**
  - 作为 ${story.role}，我想要 ${story.feature}，以便于 ${story.benefit}`).join('\n');
  }

  formatRequirementMatrix(matrix) {
    return Object.entries(matrix.classification)
      .map(([category, items]) => `### ${this.formatCategoryName(category)}
${items.map(item => `- ${item}`).join('\n')}`)
      .join('\n\n');
  }

  formatMoSCoW(priorities) {
    return `**Must Have (必须有)**:
${priorities.mustHave.map(p => `- ${p}`).join('\n')}

**Should Have (应该有)**:
${priorities.shouldHave.map(p => `- ${p}`).join('\n')}
...`;
  }

  formatFunctionalRequirements(reqs) {
    return `
${reqs.features.map(f => `- **${f}**: 核心功能需求`).join('\n')}
`;
  }

  formatUserStories(stories) {
    return stories.map(s => `- **${s.title}**
  - 作为 ${s.role}，我想要 ${s.feature}，以便于 ${s.benefit}`).join('\n');
  }

  formatAcceptanceCriteria(criteria) {
    return criteria.map(c => `- [ ] **${c.requirement}**: ${c.description}`).join('\n');
  }

  // Helper methods
  assessComplexity(text) {
    return text.includes('协作') || text.includes('实时') || text.includes('支付') ? '复杂' : '中等';
  }

  identifyStakeholders(text) {
    return text.includes('用户') ? ['终端用户'] : 
           text.includes('管理员') ? ['管理员', '终端用户'] : 
           ['项目团队'];
  }

  calculateCoverage(categories) {
    return {
      auth: categories.classification.authentication?.length || 0,
      core: categories.classification.core?.length || 0,
      comm: categories.classification.communication?.length || 0,
      data: categories.classification.data?.length || 0,
      admin: categories.classification.admin?.length || 0
    };
  }

  identifyGaps(criteria) {
    return ['安全审计', '数据备份', '权限管理'];
  }

  formatCategoryName(category) {
    return {
      authentication: '认证与授权',
      core: '核心业务功能',
      communication: '通信与通知',
      data: '数据管理',
      admin: '后台管理',
      integrations: '第三方集成'
    }[category] || category;
  }

  extractFeatures(text, keywords) {
    const features = [];
    for (const keyword of keywords) {
      if (text.includes(keyword)) {
        features.push(keyword + (text.includes('的') ? '相关的功能' : ''));
      }
    }
    return features;
  }

  extractNFRs(text, keywords) {
    const nfrs = [];
    for (const keyword of keywords) {
      if (text.includes(keyword)) {
        nfrs.push(keyword);
      }
    }
    return nfrs;
  }

  formatUserStory(feature) {
    return {
      title: this.formatCategoryName(feature),
      role: '相关用户',
      feature: feature,
      benefit: '完成业务目标'
    };
  }
}
