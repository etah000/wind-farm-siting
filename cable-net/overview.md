# OptiWindNet 中文概述

> 本文档基于项目源码、文档与示例 Notebook 综合整理而成。

---

## 一、项目功能概述

**OptiWindNet** 是由丹麦技术大学（DTU Wind，TOPFARM 项目组）开发的开源 Python 工具包，专用于设计和优化风电场**集电网络**（collection system / cable network）。

其核心任务是：给定风电场中风机与变电站的地理位置（以及可能存在的区域边界和障碍物），自动确定每台风机与哪一段海缆相连、哪些风机组成一条馈线（feeder）回路、以及如何在地图上实际铺设这些缆线——从而使总布线长度或总成本最小，同时满足一系列工程约束。

### 主要功能

| 功能 | 说明 |
|------|------|
| **拓扑优化** | 决定哪些风机连接在一起形成树形/链式馈线结构 |
| **路由优化** | 确定缆线在地图上避开障碍物的实际路径 |
| **电缆选型** | 根据每段线路的负载自动分配最合适（最经济）的电缆型号 |
| **梯度计算** | 对风机坐标与变电站坐标计算长度/成本梯度，可与 TOPFARM 联合优化 |
| **多种求解器** | 支持启发式（EW）、元启发式（HGS、LKH）、精确解（MILP/MIP）三大类 |
| **可视化** | 内置 matplotlib/SVG 绘图，支持 Jupyter Notebook 内联渲染 |
| **多种数据格式** | 支持 NumPy 数组、YAML（自定义 / WindIO 协议）、OSM.PBF 三种输入格式 |
| **内置案例库** | 包含 80+ 个真实海上风电场位置数据（如 Horns Rev、Dogger Bank、Hornsea 等） |

### API 分层

OptiWindNet 提供两套接口：

- **Network/Router API（高级）**：通过 `WindFarmNetwork` 和 `Router` 两个类封装全部功能，适合快速上手和生产环境使用。
- **Advanced API（低级）**：直接操作 `networkx.Graph` 数据结构及各独立函数，适合自定义算法、研究与扩展。

---

## 二、布线优化与变电站选择的实现原理

### 2.1 问题建模

OptiWindNet 将集电网络设计建模为**有容量限制的最小生成树（C-MST）/ 有容量限制的车辆路径（CVRP）混合图优化问题**：

- **节点**：风机（terminals，编号 `0..T-1`）和变电站（root nodes，编号 `-R..-1`）
- **边**：两点之间可敷设缆线的候选连接
- **目标**：在满足约束的前提下，最小化全部缆线的总长度或总造价

核心约束：
1. 电路只能在风机处分支，不得在缆线中途分叉（拓扑约束）；
2. 缆线路径不能互相交叉（路由约束）；
3. 缆线路径必须位于允许敷设区域内，避开所有障碍物（几何约束）；
4. 单根馈线连接的风机数量不超过最大容量 `capacity`（电气约束）。

### 2.2 输入参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `turbinesC` | `ndarray (T, 2)` | 每台风机的平面坐标 `(x, y)`，通常为 UTM 投影坐标（米） |
| `substationsC` | `ndarray (R, 2)` | 每座变电站（OSS）的坐标；支持多变电站情形 |
| `borderC` | `ndarray (B, 2)` | 围合允许敷设区域的多边形顶点（逆时针） |
| `obstacleC_` | `list[ndarray]` | 障碍区多边形列表（顺时针，如锚地、保护区）；可为空 |
| `cables` | `int \| list[tuple]` | 可用电缆规格：`[(容量, 单位长度造价), ...]`，容量单位为可接入风机数 |

也可通过以下方式从文件批量装载地理数据：
- `WindFarmNetwork.from_yaml(filepath)` — 读取 OptiWindNet YAML 格式
- `WindFarmNetwork.from_pbf(filepath)` — 读取 OpenStreetMap PBF 格式
- `WindFarmNetwork.from_windIO(filepath)` — 读取 IEA WindIO YAML 格式
- `load_repository()` — 一次性加载内置的所有真实风电场数据

所有地理数据统一封装在 `networkx.Graph` 对象 `L` 中，节点属性 `kind` 区分 `'wtg'`（风机）和 `'oss'`（变电站）。

### 2.3 输出结果

| 输出 | 说明 |
|------|------|
| `wfn.S`（`nx.Graph`） | **拓扑解**：选定的连接关系（哪些节点相连），不含具体路由 |
| `wfn.G`（`nx.Graph`） | **路由集**：含每段缆线的实际路径（含绕障虚拟节点）及电缆型号属性 |
| `wfn.length()` | 全场缆线总长度（米） |
| `wfn.cost()` | 全场缆线总造价（依电缆单位造价加权求和） |
| `wfn.gradient()` | 全场总长度或总造价对每台风机/变电站位置的梯度 |
| `wfn.solution_info()` | 求解器运行信息（运行时间、目标值、MIP 间隙、终止条件等） |

### 2.4 整体算法流程

```
输入（风机 + 变电站 + 边界 + 障碍 + 电缆规格）
        │
        ▼
① 构建位置图 L（networkx.Graph，含坐标与拓扑约束标记）
        │
        ▼
② 约束 Delaunay 三角化（调用 CDT / PythonCDT 库）
   → 生成导航网格 P（PlanarEmbedding）
   → 生成候选连接图 A（Available Links Graph）
        │
        ▼
③ 【多变电站】聚类分配（clusterize()）
   将风机按距离分配到最近变电站，保证负载均衡
        │
        ▼
④ 拓扑求解（依 Router 类型选择求解方法）
   ├── EWRouter  → 改进 Esau-Williams 启发式（毫秒级）
   ├── HGSRouter → HGS-CVRP 元启发式（秒级，仅产生链形拓扑）
   └── MILPRouter→ MILP 精确模型（分钟级，可提供最优性证明）
        │ 输出拓扑解 S
        ▼
⑤ 路由求解（PathFinder，漏斗算法）
   在三角网格上为每段连接寻找无交叉、绕障的最短路径
   必要时插入绕障虚拟节点（detour vertices）
        │ 输出路由集 G（含实际路径坐标）
        ▼
⑥ 电缆分配（assign_cables()）
   按各段线路下游风机数（负载）选择最小满足容量的电缆型号
        │
        ▼
最终输出：G（拓扑 + 路由 + 电缆型号 + 造价/长度属性）
```

> **注意**：OptiWindNet **不包含**变电站选址（substation siting）模块。变电站位置须由用户在优化前通过坐标输入确定。

### 2.5 三类求解器详解

#### EWRouter — 快速启发式

基于 **Esau-Williams C-MST 启发式**的改进版本，核心思想是从星形初始解（每台风机直连最近变电站）出发，通过贪心合并逐步将短距直连替换为更经济的串联回路。

改进点：
- 以约束 Delaunay 三角化限制搜索空间（仅考虑相邻候选连接）；
- 内置**线路交叉检测与避免**（原始 Esau-Williams 不含此约束）；
- 可调变体：`esau_williams`（经典）、`biased_EW`（偏向根节点方向）、`rootlust`（可调强度的根节点吸引力）、`radial_EW`（强制链形拓扑）。

特点：运行时间毫秒级，适合初始解生成和为 MILP 提供热启动。

#### HGSRouter — 元启发式

使用 **HGS-CVRP**（Hybrid Genetic Search for CVRP，Vidal 2022），将集电网络问题等价映射为有容量限制的车辆路径问题，利用混合遗传搜索求解，支持包含 SWAP* 邻域搜索。

特点：
- **只产生链形（radial）拓扑**（每台风机最多两个连接节点，如同一条串联链）；
- 支持馈线数量约束（`feeder_limit`）与负载均衡（`balanced`）；
- 运行时间秒级，解质量优于 EWRouter。

#### MILPRouter — 精确数学规划

将问题建模为混合整数线性规划（MILP），支持如下求解器：
- **开源**：OR-Tools（CP-SAT / gSCIP 后端）、CBC、SCIP、HiGHS
- **商业**：Gurobi、IBM CPLEX

支持热启动（将已有启发式解作为初始可行解传入）。可通过 `ModelOptions` 精细控制：
- 拓扑类型：`branched`（分支）/ `radial`（链形）
- 馈线数量：`unlimited` / `minimum` / `specified` / `min_plus1` 等
- 负载均衡约束
- 求解时间上限与 MIP 最优性间隙容忍度

### 2.6 导航网格构建（约束 Delaunay 三角化）

在拓扑求解前，OptiWindNet 对所有节点（风机、变电站、边界顶点、障碍顶点）进行**约束 Delaunay 三角化**（Constrained Delaunay Triangulation，CDT，通过 `artem-ogre/PythonCDT` 库实现）：

- CDT 将整个区域剖分为若干三角形；
- 边界和障碍物的边被设置为**约束边**（不可穿越）；
- 由三角化生成的平面嵌入图 `P`（`PlanarEmbedding`）作为导航网格；
- 三角化的 Delaunay 邻接关系决定哪些节点之间可以考虑连接，从而生成候选连接图 `A`。

这一步将问题从完全图（$O(T^2)$ 条边）压缩为稀疏图，在大幅减少变量数的同时保留了最优解的可达性。

### 2.7 路由算法（PathFinder）

拓扑解 `S` 确定后，`PathFinder` 在三角化导航网格上为每条选定连接计算实际铺缆路径：

- 采用**漏斗算法（funnel algorithm）**，沿着三角形走廊（channel）推进，通过门（portal）逐步收窄漏斗，求得最短可行路径；
- 当路径需要绕过障碍物或已有缆线时，算法在约束边上行走（chain-walk），自动处理多条缆线共享约束边的情形；
- 若路径发生绕障，算法插入**绕障虚拟节点**（detour vertices）记录实际路径折点；
- 所有路径保证无交叉（满足路由约束的核心机制）。

---

## 三、与 AEP 评估和布局优化的协同关系

### 3.1 工具边界：OptiWindNet 负责什么，不负责什么

从风电场总体方案设计看，OptiWindNet 解决的是**集电网络优化**问题，而不是风资源评估或风场尾流仿真问题。它的输入是风机与变电站坐标、边界、障碍物和电缆规格，输出是网络拓扑、实际路径、总长度和总造价。它**不直接计算**以下内容：

- 风场年发电量（AEP）；
- 风机间尾流损失；
- 风机功率曲线对应的逐工况出力；
- 风资源长期订正、风速风向联合频率统计；
- 机位坐标本身的发电收益最优解。

因此，在完整的风电场技术方案中，OptiWindNet 更适合作为“**电气集电系统子模块**”接入总流程，与 FLORIS、TOPFARM、reV 或自定义 AEP 评估模型配合使用。

### 3.2 为什么要与 AEP 评估联动

风场方案优选通常不能只看缆线长度最短，还需要同时考虑发电收益。因为机位排布一旦改变，既会改变尾流损失和净发电量，也会改变集电网络的线路长度、馈线结构和电缆选型。

在风场级评价中，AEP 的核心计算可写为：

$$
AEP = 8760 \cdot \sum_i \sum_j P_{farm}(wd_i, ws_j) \cdot f(wd_i, ws_j)
$$

其中：

- $P_{farm}(wd_i, ws_j)$ 是某一风向、风速工况下全场总功率；
- $f(wd_i, ws_j)$ 是该工况的联合频率；
- 8760 是全年小时数。

对单个布局方案而言，AEP 侧反映的是“**发多少电**”，而 OptiWindNet 侧反映的是“**这些风机如何以更低成本接入变电站**”。如果项目目标是最小化 LCOE 或进行投标阶段综合排序，就必须把两者联合起来看。

### 3.3 推荐的联合技术路线

将 [docs/tender-gemini.md](../docs/tender-gemini.md) 中的 AEP 思路合并到 cable-net 场景后，更合理的总体流程是：

1. **风资源与边界准备**：整理测风、风向风速联合频率、场址边界、禁建区和候选机位约束。
2. **风场布局与 AEP 评估**：使用 FLORIS、TOPFARM 或其他尾流模型，对候选布局计算净发电量、尾流损失率和容量因子。
3. **集电网络优化**：将选定布局的风机坐标、变电站坐标、边界和障碍物传入 OptiWindNet，求解缆线路径、馈线结构和电缆成本。
4. **综合指标回算**：将 AEP 结果与集电网络 CAPEX 汇总，计算 LCOE、单位千瓦静态投资或投标所需的综合经济指标。
5. **迭代比选**：若新的布线成本或绕障结果过高，则回到布局层重新调整机位，再重复上述流程。

这种流程对应的是“**发电侧模型 + 电气侧模型**”的分层耦合结构。AEP 模型负责尾流与能量产出，OptiWindNet 负责几何可行且经济的集电网络，两者各自专注本领域，工程上更稳健。

### 3.4 数据接口与联合优化的关键点

在工程实现中，两类模型之间最关键的共享变量是**风机坐标**和**变电站坐标**。

| 模块 | 主要输入 | 主要输出 | 对另一模块的影响 |
|------|------|------|------|
| **AEP / 尾流模型** | 风机坐标、机型参数、风况频率、空气密度、湍流强度 | 总 AEP、单机 AEP、尾流损失率、容量因子 | 为布线方案提供收益侧评价基准 |
| **OptiWindNet** | 风机坐标、变电站坐标、边界、障碍物、电缆规格 | 网络拓扑、路径、长度、造价、电缆型号 | 为布局方案提供电气侧成本和可实施性反馈 |

这里需要特别注意三点：

1. **OptiWindNet 不做尾流约束**。如果某个布局在布线上很优，但机位间距过近导致尾流损失很大，那么该问题必须由上游 AEP 模型识别。
2. **AEP 模型通常不做真实布线绕障**。即使某个布局在发电量上占优，若其跨越道路、沟谷、保护区后导致线路成本急剧上升，仍需由 OptiWindNet 进行电气复核。
3. **综合目标通常不是单目标**。投标或方案优选更常见的目标是最小化 LCOE、在预算约束下最大化 AEP，或在容量、边界、电缆约束下寻找收益与成本的折中解。

### 3.5 适合并入本仓库的表述方式

如果本仓库后续要形成“陆上风电场总体优化方案”文档，可以把角色分工概括为：

- **FLORIS / AEP 模块**：负责风资源、尾流、年发电量和布局收益评估；
- **OptiWindNet / cable-net 模块**：负责集电网络拓扑、路径绕障和电缆成本优化；
- **外层优化器**：负责在 AEP、CAPEX、约束条件之间进行联合迭代，最终形成可投标、可研或微观选址阶段的综合方案。

按这个口径，OptiWindNet 在整个项目中不是替代 AEP 模型，而是补足“**布局方案落到真实电气接入系统后是否仍然经济可行**”这一关键环节。

---

## 四、在陆地风电场中的适用性

### 4.1 结论：技术上完全可用

OptiWindNet 的全部核心算法——约束 Delaunay 三角化、Esau-Williams 启发式、HGS-CVRP 元启发式、MILP 精确模型——**均为通用平面图优化算法，与海上/陆上环境无本质区别**。

项目内部统一使用平面笛卡尔坐标（通常为 UTM 投影坐标，单位米），只要将陆地风机与变电站的 UTM 坐标正确输入，优化逻辑与海上场景完全相同。**忽略地形高程差时**，OptiWindNet 完全适用于陆地风电场。

### 4.2 陆上场景的注意事项

| 方面 | 说明 |
|------|------|
| **地形高程** | 项目当前不考虑高程差对实际电缆长度的影响；若地形复杂，需在输入前将三维路径长度折算为等效平面距离 |
| **电缆容量单位** | `capacity` 以"可接入风机数"为单位，与交流/直流、电压等级无关；按实际电缆额定电流换算即可 |
| **障碍物建模** | 陆地典型障碍（公路、建筑物、自然保护区等）均可建模为多边形障碍物 `obstacleC_` 输入 |
| **变电站位置** | 项目不含变电站选址模块，但陆上变电站通常已有既定位置，直接传入坐标即可 |

### 4.3 项目中的相关示例

项目中**没有明确标注为陆地风电场的示例**。内置的 80+ 个案例数据均来自真实海上风电场（北海、英国、波罗的海、中国近海等）。但以下示例可佐证其通用性：

#### 示例 1：CVRP 学术基准算例（Notebook `41-Paper_3.1_Queiroga_2021_CVRP_instances.ipynb`）

本 Notebook 将 OptiWindNet 应用于 Queiroga 等人（2021）发布的经典 CVRP 学术基准测试集。这些算例来源于**物流配送路径规划**领域，节点坐标为抽象平面点，与海上环境完全无关。

实验目的：验证以约束 Delaunay 三角化稀疏化搜索空间（而非完全图）能否保留最优解质量——结论是肯定的，且在大规模算例中显著减少了 MILP 变量数量，求解速度大幅提升。

这直接证明 OptiWindNet 的底层算法兼容任意平面节点布局，不局限于海上风电场。

#### 示例 2：合成风电场工具（`optiwindnet.synthetic` 模块）

`synthetic.py` 模块提供了两个通用工具：
- `toyfarm()`：返回一个含 12 台风机 + 1 座变电站的标准测试场 `L` 对象，可直接用于功能验证；
- `L_from_synthetic(RootC, TerminalC, BorderC=None)`：从任意 NumPy 坐标数组生成 `L` 图。

用户可直接传入陆地风电场的任意坐标数组生成 `L`，再调用 `WindFarmNetwork` 优化，与海上场景的使用方式完全一致。

### 4.4 陆地风电场使用示例（可直接运行）

以下示例展示如何将 OptiWindNet 的优化流程应用于一个假设的陆地风电场：

```python
import numpy as np
from optiwindnet.api import WindFarmNetwork, EWRouter, MILPRouter, ModelOptions

# ── 陆地风电场布局（坐标单位：米，UTM 平面坐标）──────────────────────
turbinesC = np.array([
    [1000, 2000], [1500, 2000], [2000, 2000],
    [1000, 2500], [1500, 2500], [2000, 2500],
    [1000, 3000], [1500, 3000], [2000, 3000],
    [1500, 3500],
], dtype=float)

substationsC = np.array([[1500, 1000]], dtype=float)   # 变电站位置

# 风电场边界（逆时针多边形）
borderC = np.array([
    [500,  500], [2500,  500],
    [2500, 4000], [500,  4000],
], dtype=float)

# 障碍物（如公路用地，顺时针多边形）
road = np.array([
    [1200, 2200], [1800, 2200],
    [1800, 2300], [1200, 2300],
], dtype=float)

# 电缆规格：[(最大接入风机数, 单位长度造价), ...]
cables = [(3, 1.0), (6, 1.4), (10, 1.8)]

# ── 创建 WindFarmNetwork 实例 ─────────────────────────────────────────
wfn = WindFarmNetwork(
    cables=cables,
    turbinesC=turbinesC,
    substationsC=substationsC,
    borderC=borderC,
    obstacleC_=[road],
    name='示例陆地风电场',
)

# ── 快速启发式求解（毫秒级）──────────────────────────────────────────
wfn.optimize(router=EWRouter())
print(f'EWRouter 总长度：{wfn.length():.0f} 米，总造价：{wfn.cost():.2f}')

# ── 精确 MILP 求解（以 EWRouter 解作为热启动）────────────────────────
milp = MILPRouter(
    solver_name='ortools.cp_sat',
    time_limit=30,
    mip_gap=0.005,
    model_options=ModelOptions(topology='branched', feeder_limit='minimum'),
)
wfn.optimize(router=milp)
print(f'MILPRouter 总长度：{wfn.length():.0f} 米，总造价：{wfn.cost():.2f}')
print(wfn.solution_info())

# ── 可视化 ────────────────────────────────────────────────────────────
wfn.plot()
```

**说明**：
- `borderC` 定义允许铺缆的地块边界，`obstacleC_` 定义禁止穿越的障碍区（公路、建筑、保护区等）；
- OptiWindNet 会自动确保所有缆线路径在边界内且绕开障碍物；
- 通过先运行 `EWRouter` 再运行 `MILPRouter`，后者会自动接收前者的解作为热启动，通常能加速求解。

---

## 五、项目结构速览

```
optiwindnet/
├── api.py              # 高级 API：WindFarmNetwork、EWRouter、HGSRouter、MILPRouter
├── interarraylib.py    # 核心数据结构：图构建、负载计算（calcload）、电缆分配（assign_cables）
├── mesh.py             # 约束 Delaunay 三角化 + 平面嵌入（导航网格 P 和候选图 A）
├── pathfinding.py      # 漏斗算法（PathFinder）：在三角网格上计算无交叉最短路由
├── crossings.py        # 交叉检测工具函数
├── geometric.py        # 几何工具（角度、旋转、完全图构建等）
├── clustering.py       # 多变电站场景下的风机聚类分配
├── heuristics/         # 启发式算法（constructor、Esau-Williams 各变体）
├── baselines/          # 元启发式封装（HGS-CVRP、LKH TSP solver）
├── MILP/               # MILP 精确模型及求解器接口（ortools、gurobi、cplex、cbc、scip、highs）
├── importer.py         # 数据导入（YAML、PBF、WindIO、内置案例库）
├── synthetic.py        # 合成/测试场景生成（toyfarm、L_from_synthetic）
├── augmentation.py     # 图增强工具
├── repair.py           # 解修复工具
├── plotting.py         # matplotlib 可视化（gplot、pplot）
├── svg.py              # SVG 导出（svgplot）
└── data/               # 内置真实风电场数据（80+ 个 YAML / OSM.PBF 文件）
```

---

## 六、引用与致谢

**核心论文**：
> Mauricio Souza de Alencar, Tuhfe Göçmen, Nicolaos A. Cutululis,
> *Flexible cable routing framework for wind farm collection system optimization*,
> European Journal of Operational Research, 2026, Vol. 329, No. 3, pp. 1037–1051.
> <https://doi.org/10.1016/j.ejor.2025.07.069>

**软件包引用**：
> Souza de Alencar, M., Arasteh, A., & Friis-Møller, M. (2026). OptiWindNet by DTU Wind Energy. Zenodo.
> <https://doi.org/10.5281/zenodo.18388438>

**关键依赖**：
- [vidalt/HGS-CVRP](https://github.com/vidalt/HGS-CVRP)（HGS 元启发式，via [mdealencar/HybGenSea](https://github.com/mdealencar/HybGenSea)）
- [artem-ogre/CDT](https://github.com/artem-ogre/CDT)（约束 Delaunay 三角化，via [artem-ogre/PythonCDT](https://github.com/artem-ogre/PythonCDT)）

本项目由丹麦独立研究基金（DFF，项目编号 1127-00188B）资助，作为丹麦技术大学博士研究的一部分开展。
