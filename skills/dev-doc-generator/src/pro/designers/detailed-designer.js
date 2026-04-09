/**
 * Detailed Designer - 详细设计模块
 * 
 * 功能:
 * 1. 低级接口实现设计
 * 2. 数据库 Schema 设计
 * 3. API 详细设计
 * 4. 错误处理策略
 * 5. 代码结构设计
 */

export class DetailedDesigner {
  constructor(requirements, architecture) {
    this.requirements = requirements;
    this.architecture = architecture;
  }

  async generate() {
    return {
      interfaceImplementations: this.generateInterfaceImplementations(),
      databaseSchema: this.generateDatabaseSchema(),
      dataFlowDiagram: this.generateDataFlowDiagram(),
      algorithmDesigns: this.generateAlgorithmDesigns(),
      structurePatterns: this.generateStructurePatterns(),
      errorHandlingStrategy: this.generateErrorHandlingStrategy(),
      codingStandards: this.generateCodingStandards()
    };
  }

  generateInterfaceImplementations() {
    return [
      {
        module: '认证模块',
        interfaces: [
          {
            name: 'AuthService',
            methods: ['login', 'register', 'logout', 'refreshToken'],
            signature: `
interface AuthService {
  login(email: string, password: string): Promise<AuthResult>;
  register(userData: RegisterData): Promise<User>;
  logout(token: string): Promise<boolean>;
  refreshToken(refreshToken: string): Promise<TokenPair>;
}`,
            implementation: `class AuthService {
  constructor(private tokenService: TokenService, 
              private userService: UserService,
              private cryptoService: CryptoService) {}

  async login(email: string, password: string): Promise<AuthResult> {
    // 1. 验证用户存在
    const user = await this.userService.findByEmail(email);
    if (!user) throw new ValidationError('User not found');
    
    // 2. 验证密码
    const isValid = await this.cryptoService.comparePassword(password, user.passwordHash);
    if (!isValid) throw new ValidationError('Invalid credentials');
    
    // 3. 生成 JWT
    const tokens = await this.tokenService.generateTokenPair(user);
    
    // 4. 记录登录日志
    await this.auditLogger.log('user_login', user.id);
    
    return tokens;
  }

  async register(userData: RegisterData): Promise<User> {
    // 1. 检查邮箱唯一性
    const existing = await this.userService.findByEmail(userData.email);
    if (existing) throw new ConflictError('Email already exists');
    
    // 2. 密码加密
    const hashedPassword = await this.cryptoService.hashPassword(userData.password);
    
    // 3. 创建用户
    const user = await this.userService.create({
      ...userData,
      passwordHash: hashedPassword
    });
    
    // 4. 生成 token
    const tokens = await this.tokenService.generateTokenPair(user);
    
    return { user, tokens };
  }
}`
          },
          {
            name: 'UserService',
            methods: ['getUserById', 'updateUser', 'deleteUser'],
            signature: `
interface IUserService {
  getUserById(id: string): Promise<User | null>;
  updateUser(id: string, data: UpdateUserDto): Promise<User>;
  deleteUser(id: string): Promise<boolean>;
}`,
            implementation: `class UserService {
  constructor(private db: Database, private cache: CacheService) {}

  async getUserById(id: string): Promise<User | null> {
    // 1. 检查缓存
    const cached = await this.cache.get(\`user:\${id}\`);
    if (cached) return cached;
    
    // 2. 查询数据库
    const user = await this.db.query(\`
      SELECT * FROM users WHERE id = \$1
    \`, [id]);
    
    if (!user) return null;
    
    // 3. 更新缓存
    await this.cache.set(\`user:\${id}\`, user, 3600);
    
    return user;
  }

  async updateUser(id: string, data: UpdateUserDto): Promise<User> {
    // 1. 验证用户存在
    const existing = await this.getUserById(id);
    if (!existing) throw new NotFoundError('User not found');
    
    // 2. 检查邮箱唯一性 (如果修改了邮箱)
    if (data.email && data.email !== existing.email) {
      const duplicate = await this.findByEmail(data.email);
      if (duplicate) throw new ConflictError('Email already in use');
    }
    
    // 3. 更新记录
    const updated = await this.db.query(\`
      UPDATE users SET 
        email = \$1, 
        username = \$2,
        updated_at = NOW()
      WHERE id = \$3
      RETURNING *
    \`, [data.email, data.username, id]);
    
    // 4. 刷新缓存
    await this.cache.del(\`user:\${id}\`);
    
    // 5. 审计日志
    await this.auditLogger.log('user_update', id, existing, updated);
    
    return updated;
  }
}`
          }
        ]
      },
      {
        module: '核心业务模块',
        interfaces: [
          {
            name: 'OrderProcessor',
            methods: ['createOrder', 'processPayment', 'fulfillOrder'],
            signature: `
interface IOrderProcessor {
  createOrder(data: CreateOrderDto): Promise<Order>;
  processPayment(orderId: string): Promise<PaymentResult>;
  fulfillOrder(orderId: string): Promise<Shipment>;
}`,
            detail: '订单处理流程：验证库存 -> 冻结库存 -> 创建订单 -> 处理支付 -> 通知发货'
          }
        ]
      }
    ];
  }

  generateDatabaseSchema() {
    return [
      `-- Users 表
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(100),
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(200),
  avatar_url TEXT,
  phone_number VARCHAR(20),
  is_active BOOLEAN DEFAULT true,
  is_admin BOOLEAN DEFAULT false,
  email_verified_at TIMESTAMPTZ,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);`,

      `-- Users 索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active, created_at);`,

      `-- Sessions 表
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  refresh_token VARCHAR(512) UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  revoked_at TIMESTAMPTZ
);`,

      `-- Session 索引
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
CREATE INDEX idx_sessions_token ON sessions(refresh_token);`,

      `-- Audit Logs 表
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  action VARCHAR(100) NOT NULL,
  resource_type VARCHAR(50),
  resource_id UUID,
  previous_values JSONB,
  new_values JSONB,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);`,

      `-- Audit Logs 索引
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);`
    ];
  }

  generateDataFlowDiagram() {
    return `
sequenceDiagram
    participant U as User
    participant C as Client
    participant A as API Gateway
    participant S as Service Layer
    participant D as Database
    participant E as External API

    U->>C: 1. 发起请求
    C->>A: 2. 转发请求
    A->>A: 3. 认证与验证
    A->>S: 4. 调用服务
    S->>D: 5. 查询数据库
    D-->>S: 6. 返回数据
    S-->>A: 7. 响应结果
    A-->>C: 8. 返回 JSON
    C-->>U: 9. 渲染结果
    
    Note right of S: 9. 触发异步任务
    S->>E: 10. 发送外部通知
    E-->>S: 11. 确认发送
`;
  }

  generateAlgorithmDesigns() {
    return [
      {
        name: '密码哈希算法',
        description: '使用 bcrypt 进行密码存储',
        pseudocode: `function hashPassword(password: string): Promise<string> {
  // 1. 随机盐值生成 (12 位)
  const salt = randomBytes(12);
  
  // 2. bcrypt hashing (成本因子 10-12)
  const hash = bcrypt.hashSync(password, SALT_ROUNDS);
  
  return hash;
}`,
        complexity: 'O(n) where n = SALT_ROUNDS'
      },
      {
        name: 'JWT 令牌生成',
        description: '访问令牌和刷新令牌组合',
        pseudocode: `function generateTokenPair(user: User): TokenPair {
  const access = jwt.sign({
    sub: user.id,
    email: user.email,
    role: user.role,
    iat: Math.floor(Date.now() / 1000)
  }, ACCESS_TOKEN_SECRET, {
    expiresIn: '15m'
  });

  const refresh = jwt.sign({
    uid: user.id,
    type: 'refresh'
  }, REFRESH_TOKEN_SECRET, {
    expiresIn: '7d'
  });

  return {
    accessToken: access,
    refreshToken: refresh,
    expiresIn: 900
  };
}`,
        complexity: 'O(1)'
      },
      {
        name: '库存检查算法',
        description: '分布式环境下的库存扣减',
        pseudocode: `async function reserveInventory(
  productId: string,
  quantity: number,
  requestId: string
): Promise<boolean> {
  // 1. 分布式锁获取
  const lock = await redis.set(
    \`inventory_lock:\${productId}\`,
    requestId,
    'PX',
    LOCK_TTL,
    'NX'
  );

  if (!lock) throw new ConflictError('Inventory locked');

  try {
    // 2. 当前库存查询
    const current = await inventoryRepository.get(productId);
    
    if (current < quantity) {
      throw new InsufficientInventoryError();
    }
    
    // 3. 乐观锁更新
    const updated = await inventoryRepository.updateWithVersion(
      productId,
      quantity,
      current.version
    );
    
    return updated;
  } finally {
    // 4. 释放锁
    await redis.del(\`inventory_lock:\${productId}\`);
  }
}`,
        complexity: 'O(log n) with Redis lock'
      }
    ];
  }

  generateStructurePatterns() {
    return {
      directoryStructure: `
src/
├── api/                   # API 层
│   ├── controllers/       # 请求处理器
│   │   ├── auth.ts
│   │   ├── users.ts
│   │   └── orders.ts
│   ├── routes/            # 路由定义
│   │   ├── auth.ts
│   │   ├── users.ts
│   │   └── index.ts
│   └── middlewares/       # 中间件
│       ├── auth.ts
│       ├── validation.ts
│       └── errorHandler.ts
│
├── application/           # 应用层 (Use Cases)
│   ├── useCases/
│   │   ├── auth/
│   │   │   ├── login.ts
│   │   │   ├── register.ts
│   │   │   └── refreshToken.ts
│   │   ├── user/
│   │   │   ├── getUser.ts
│   │   │   └── updateUser.ts
│   │   └── order/
│   │       ├── createOrder.ts
│   │       └── processPayment.ts
│   └── services/          # Application Services
│       ├── AuthService.ts
│       ├── UserService.ts
│       └── OrderService.ts
│
├── domain/                # 领域层 (核心业务)
│   ├── entities/          # 领域实体
│   │   ├── User.ts
│   │   ├── Order.ts
│   │   └── Product.ts
│   ├── valueObjects/      # 值对象
│   │   ├── Email.ts
│   │   ├── Money.ts
│   │   └── Address.ts
│   ├── repositories/      # 仓储接口 (抽象)
│   │   ├── UserRepository.ts
│   │   └── OrderRepository.ts
│   └── events/            # 领域事件
│       ├── UserRegistered.ts
│       └── OrderCreated.ts
│
├── infrastructure/        # 基础设施层
│   ├── database/          # 数据访问实现
│   │   ├── postgres/
│   │   │   ├── UserRepository.ts
│   │   │   └── OrderRepository.ts
│   │   └── redis/         # Redis 实现
│   │       └── CacheService.ts
│   ├── auth/              # 认证实现
│   │   ├── tokenService.ts
│   │   └── passwordService.ts
│   └── external/          # 外部服务
│       ├── paymentService.ts
│       └── emailService.ts
│
├── shared/                # 共享模块
│   ├── types/             # TypeScript 类型
│   ├── errors/            # 自定义错误
│   ├── constants/         # 常量定义
│   └── utils/             # 工具函数
│
├── config/                # 配置管理
│   ├── index.ts
│   ├── database.config.ts
│   └── app.config.ts
│
├── tests/                 # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── app.ts                 # 应用入口
`,
codePatterns: [
      {
        name: 'Service Layer Pattern',
        description: '业务逻辑与服务层的分离',
        code: `// Application Service (业务逻辑)
class CreateOrderService {
  constructor(
    private orderRepository: OrderRepository,
    private inventoryService: InventoryService,
    private paymentService: PaymentService
  ) {}

  async execute(dto: CreateOrderDto): Promise<Order> {
    // 1. 验证用户
    const user = await this.validateUser();
    
    // 2. 检查库存
    await this.validateInventory(dto.items);
    
    // 3. 创建订单
    const order = this.createOrder(user, dto);
    
    // 4. 保存订单
    return await this.orderRepository.save(order);
  }
}

// Repository Implementation (数据访问)
class PostgresOrderRepository implements OrderRepository {
  async save(order: Order): Promise<Order> {
    const result = await this.db.query(\`
      INSERT INTO orders (...) VALUES (...)
      RETURNING *
    \`, [/* values */]);
    return result.rows[0];
  }
}`
      },
      {
        name: 'DTO Pattern',
        description: '数据传输对象',
        code: `// Request DTOs
interface CreateUserDto {
  email: string;
  password: string;
  username: string;
}

// Response DTOs
interface UserResponse {
  id: string;
  email: string;
  username: string;
  displayName: string;
  createdAt: Date;
}

// Query DTOs
interface GetUserQueryDto {
  sortBy?: 'createdAt' | 'email';
  sortOrder?: 'ASC' | 'DESC';
  limit?: number;
  offset?: number;
}`
      }
    ]
  };
}

  generateErrorHandlingStrategy() {
    return `
## 错误处理策略

### 错误类型定义

\`\`\`typescript
// Base exception class
abstract class AppError extends Error {
  readonly statusCode: number;
  readonly isOperational: boolean;
  readonly errorCode: string;

  constructor(message: string, statusCode: number, errorCode: string) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    this.errorCode = errorCode;
  }
}

// Specific errors
class ValidationError extends AppError {
  constructor(message: string) {
    super(message, 400, 'VALIDATION_ERROR');
  }
}

class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super(\`\${resource} with id \${id} not found\`, 404, 'NOT_FOUND');
  }
}

class UnauthorizedError extends AppError {
  constructor(message: string = 'Unauthorized') {
    super(message, 401, 'UNAUTHORIZED');
  }
}

class ConflictError extends AppError {
  constructor(message: string) {
    super(message, 409, 'CONFLICT');
  }
}

class InternalError extends AppError {
  constructor(message: string) {
    super(message, 500, 'INTERNAL_ERROR');
  }
}
\`\`\`

### 中间件处理

\`\`\`typescript
// Error handler middleware
function errorHandler(
  err: AppError,
  req: Request,
  res: Response,
  next: NextFunction
) {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      success: false,
      error: {
        code: err.errorCode,
        message: err.isOperational ? err.message : 'Something went wrong',
        timestamp: new Date().toISOString()
      }
    });
  }

  // Handle unexpected errors
  logger.error(err);
  return res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_ERROR',
      message: 'Internal server error'
    }
  });
}
\`\`\`

### 错误码规范

- **VALIDATION_ERROR**: 400 - 请求参数验证失败
- **UNAUTHORIZED**: 401 - 认证失败
- **FORBIDDEN**: 403 - 权限不足
- **NOT_FOUND**: 404 - 资源不存在
- **CONFLICT**: 409 - 资源冲突
- **RATE_LIMIT_ERROR**: 429 - 请求频率限制
- **INTERNAL_ERROR**: 500 - 服务器内部错误
`;
  }

  generateCodingStandards() {
    return `
## 代码规范

### TypeScript 规范
- 始终使用 TypeScript
- strict: true 在 tsconfig
- 禁止 any 类型，除非必要

### API 设计
- RESTful 资源设计
- 统一响应格式
- API 版本控制
- OpenAPI 3.0 规范

### 命名规范
- 文件名：kebab-case (create-order-service.ts)
- 类名：PascalCase (CreateOrderService)
- 变量名：camelCase (userId)
- 常量：UPPER_SNAKE_CASE (MAX retries)
- 枚举：PascalCase+SNAKE_CASE (OrderStatus)

### 测试规范
- 代码覆盖率 > 80%
- 单元测试优先
- 集成测试验证流程
- E2E 测试关键路径
`;
  }
}
