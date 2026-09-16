# 换位块真值验真（Change Ringing Truth Verifier）

对一个**重复换位块**做精确真值判定：是否在第 0 至 N−1 步内出现重复行（撞回旧行）；
若无重复，第 N 步是否回到初始行（归位）。`repeats` 最大为 **10¹²**，判定过程
**不枚举全部步数**，而是用置换幂、循环子群陪集与模区间相交做精确计算。

- 后端：Python 3.13 + FastAPI + Pydantic
- 前端：React 18 + Vite + TypeScript
- 判据：pytest（算法/API）、Vitest（前端纯逻辑与组件）、Playwright（端到端）
- 编排：Docker Compose（可覆盖的 `WEB_PORT`、`API_PORT`，内置 `verify` 判据服务）

---

## 1. 固定语义（本仓库的唯一行为契约）

### 1.1 输入域

| 字段 | 含义 | 范围 |
| --- | --- | --- |
| `bells` | 钟数 | 整数，4 ≤ bells ≤ 12 |
| `block` | 换位块 | 1 ≤ 块长 ≤ 5000；每项是长度恰为 `bells` 的数组，且**恰含 1..bells 各一次**（一个置换） |
| `repeats` | 块重复次数 | 整数，1 ≤ repeats ≤ 1,000,000,000,000（10¹²） |

网络传输与页面输入均使用**一基钟号** `1..bells`；引擎内部使用零基位置。

### 1.2 行与步

- 第 0 步行（初始行）为升序钟号 `(1, 2, …, bells)`。
- 每一步取块中的一个换位 `p`（按 block 顺序、循环使用），令

      新行[i] = 旧行[p[i]]

  （即一基下的“新行第 i 位取旧行第 p[i] 位”。）
- 总步数 `N = 块长 × repeats`。步号从 0 开始：步 0 为初始行，块内第 j 个换位
  把步 `a×块长 + j` 带到 `a×块长 + j + 1`（a 为轮次，j 从 0 起）。

### 1.3 判定规则（顺序固定）

1. **重复判定**：只比较第 **0 至 N−1** 步的行；第 N 步**不参与**重复比较。
2. 一旦在这些步中存在两行相同，结果为 `fail / collision`，并返回**重复见证**：
   先取**第二次步号最小**的重复对；若并列，再取**第一次步号最小**；见证包含
   `first_step`、`second_step` 与该行 `row`。不输出任何其它行、不展开全场。
3. 若无重复，则检查第 N 步：
   - 第 N 步回到初始行 ⇒ `pass`（无冲突且归位）；
   - 否则 ⇒ `fail / not_home`，返回末行（第 N 步行）`final_row`。

两类失败互斥：碰撞时不返回末行；未归位时不返回见证。页面在失败后只保留该条
规范失败证据；任何新的错误都会先清空旧结果。

### 1.4 组合事实（语义推论，不是近似）

- 无冲突要求同一块内不同轮次的行永不重合：若块置换阶为 m，则同偏移最早在
  相隔 m 轮时重合，故 repeats ≤ m；归位要求 m | repeats。正整数下两者同时
  成立只能有 **repeats = m**；此外第 0 轮内前缀必须互不相同（否则同轮碰撞），
  且任意两个不同偏移不能落在同一陪集（否则相隔 1..m−1 轮必碰撞），即 L 个前缀
  两两处于 `<Q>` 的不同陪集、`L·m ≤ n!`。
- n 个钟至多有 n! 个不同行，而任一置换的阶 ≤ Landau 函数 g(n)，g(12) = 60。
  因此 **repeats = 10¹² 时 N ≥ 10¹² > 12!，数学上必然发生重复**；引擎仍会在
  常数/多项式于块长的时间内给出精确见证（不模拟一万亿步）。前端的“通过”视图
  对任何后端判定为 `pass` 的输入都成立（例如块积为恒等且块内无重复、repeats=1）。

---

## 2. HTTP 接口

`POST /api/verify`

请求：

```json
{ "bells": 4, "repeats": 3, "block": [[2, 1, 3, 4]] }
```

碰撞响应 `200`：

```json
{
  "status": "fail",
  "outcome": "collision",
  "bells": 4,
  "block_size": 1,
  "repeats": 3,
  "total_steps": 3,
  "block_order": 2,
  "witness": { "first_step": 0, "second_step": 2, "row": [1, 2, 3, 4] },
  "final_row": null
}
```

未归位响应 `200`：`outcome` 为 `"not_home"`、`witness` 为 `null`、
`final_row` 为末行；通过响应：`status` 为 `"pass"`、`outcome/witness/final_row`
均为 `null`。

校验失败统一为 `422`，错误定位到**第一个**不合法项：

```json
{ "error": { "message": "block[1] must be a permutation of 1..4, got [2, 1, 4]", "field": "block[1]" } }
```

`field` 取值：`bells`、`repeats`、`block`（整块为空/超长）或 `block[i]`
（第 i 行长度或内容非法，i 从 0 起）。另有 `GET /api/health`。

---

## 3. 精确算法（自行实现，无占位）

设块内换位依次为 p₀..p_{L−1}，按 §1.2 的作用约定，块积

- `Q = p₀ ∘ p₁ ∘ … ∘ p_{L−1}`（`compose(a,b)[i] = a[b[i]]`）；
- 块内前缀 `B₀ = id`，`B_{r+1} = B_r ∘ p_r`；
- 步 `t = a·L + r` 的行置换为 `P_t = Q^a ∘ B_r`（从升序行出发，行即置换本身）。

三要素：

1. **置换幂** `Q^a`：快速幂（平方–乘），支持到 10¹² 的精确整数指数；阶由
   不相交循环长度的 LCM 给出。
2. **循环子群陪集**：把所有前缀按左陪集 `<Q>∘B_r` 分组，陪集名取该陪集的字典序
   最小元（阶 ≤ 60，整圈枚举精确且廉价）；成员关系通过逐循环一致旋转 +
   CRT 合并（`_cyclic_exponent`）求指数 c_r，使 `B_r = Q^{c_r} ∘ rep`。
3. **模区间相交**：两步行相等化为轮次差属于某个模 m 剩余类
   `b − a ≡ c_r − c_s (mod m)`；`smallest_positive_residue` 给出剩余类与正整数
   的首个交点，`modular_interval_has_point` 判定该等差数列是否与区间
   `[1, repeats−1]` 相交，无需枚举轮次。

实现先做 O(L) 的第 0 轮扫描（同轮重复的第二次步号必小于一切跨轮候选），再只对
跨轮对做 O(L·m) 的陪集配对（m ≤ 60，块长 5000 时约 ≤ 147,500 对）。5000 个
12 钟随机换位 × 10¹² repeats 的实测耗时约 0.04 秒。

---

## 4. 本地开发

后端（需要 Python 3.13；本机可用 3.11 运行测试，镜像固定 3.13）：

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173 ，/api 代理到 127.0.0.1:8000
```

## 5. 判据（测试）

```bash
# 后端：置换原语 + 对拍暴力模拟的随机差分测试 + API/校验
cd backend && python -m pytest

# 前端单元：输入解析（错误定位首项）+ 组件交互（清空旧结果/规范证据）
cd frontend && npm run test:unit

# 端到端：自动拉起后端与前端 preview，覆盖碰撞/未归位/通过/万亿/错误清空
cd frontend && npx playwright install chromium && npm run test:e2e
```

差分测试在小规模（bells ≤ 9、repeats ≤ 40）上把精确引擎与逐行暴力模拟逐一对比，
包括见证的两步步号与行内容；另有 5000×12 钟 × 10¹² repeats 的限时判据。

## 6. Docker Compose

```bash
# 默认 WEB_PORT=8080、API_PORT=8000
docker compose up --build
# 打开 http://127.0.0.1:8080

# 覆盖宿主端口
WEB_PORT=9090 API_PORT=9000 docker compose up --build

# 容器内判据服务
docker compose run --rm verify
```

- `web`：多阶段构建（node 构建 → nginx 托管），nginx 将 `/api/` 反代到 `api:8000`。
- `api`：`python:3.13-slim` 上运行 FastAPI。
- `verify`：复用后端镜像，在容器内运行完整 pytest 判据。

## 7. 目录

```
backend/   FastAPI、Pydantic 模型、置换原语、陪集/模区间验真、pytest
frontend/  React/Vite 页面、解析与 API 客户端、Vitest、Playwright、nginx
docker-compose.yml
```
