# Auth API

认证和授权接口，基于 JWT access token + 不透明 refresh token。

## 概述

- **Access Token**: JWT (HS256)，有效期 30 分钟，通过 `Authorization: Bearer <token>` 头传递
- **Refresh Token**: 不透明 UUID 字符串，有效期 7 天，支持一次性消费（轮换）
- **密码存储**: Argon2id
- **角色**: `viewer`（只读）、`editor`（读写+ops）、`admin`（全部权限+用户管理）

## 权限矩阵

| 端点分组 | 公开 | viewer | editor | admin |
|---|:---:|:---:|:---:|:---:|
| `GET /health` | ✅ | ✅ | ✅ | ✅ |
| `POST /auth/login` | ✅ | - | - | - |
| `POST /auth/refresh` | ✅ | - | - | - |
| `GET /auth/me` | - | ✅ | ✅ | ✅ |
| `PATCH /auth/me/password` | - | ✅ | ✅ | ✅ |
| `POST /auth/logout` | - | ✅ | ✅ | ✅ |
| `GET /questions`, `GET /papers` | - | ✅ | ✅ | ✅ |
| `GET /questions/:id`, `GET /papers/:id` | - | ✅ | ✅ | ✅ |
| `POST/PATCH/DELETE/PUT` questions | - | ❌ | ✅ | ✅ |
| `POST/PATCH/DELETE/PUT` papers | - | ❌ | ✅ | ✅ |
| `POST` ops (bundles/exports/quality) | - | ❌ | ✅ | ✅ |
| `/admin/*` | - | ❌ | ❌ | ✅ |

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `QB_JWT_SECRET` | `qb-dev-secret-change-me-in-production` | JWT 签名密钥，**生产环境必须修改** |

## 初始账号

首次启动时，如果 `users` 表为空，会自动创建一个管理员账号：

- 用户名: `admin`
- 密码: `changeme`
- 角色: `admin`

**首次登录后应立即修改密码。**

## Endpoints

### `POST /auth/login`

用户名密码登录。

请求体：

```json
{
  "username": "admin",
  "password": "changeme"
}
```

成功响应 (`200`)：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "550e8400-e29b-41d4-a716-446655440000",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

错误：

- `400`: 缺少用户名或密码
- `401`: 用户名或密码错误 / 账号已停用

### `POST /auth/refresh`

使用 refresh token 获取新 token 对。旧 refresh token 在消费后立即作废（轮换）。

请求体：

```json
{
  "refresh_token": "550e8400-e29b-41d4-a716-446655440000"
}
```

成功响应同 login。

错误：

- `400`: 缺少 refresh_token
- `401`: 无效或过期的 refresh token / 账号停用

### `POST /auth/logout`

撤销当前 refresh token。

请求体：

```json
{
  "refresh_token": "550e8400-e29b-41d4-a716-446655440000"
}
```

响应 (`200`)：

```json
{
  "message": "logged out"
}
```

### `GET /auth/me`

获取当前登录用户信息。

需要 `Authorization: Bearer <access_token>`。

响应 (`200`)：

```json
{
  "user_id": "...",
  "username": "admin",
  "display_name": "Administrator",
  "role": "admin",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00.000Z",
  "updated_at": "2025-01-01T00:00:00.000Z"
}
```

### `PATCH /auth/me/password`

修改当前用户密码。

请求体：

```json
{
  "old_password": "changeme",
  "new_password": "new-secure-password"
}
```

响应 (`200`)：

```json
{
  "message": "password changed"
}
```

错误：

- `400`: 新密码少于 6 个字符
- `401`: 旧密码错误
