# TOPFARM + OptiWindNet 在线路与升压站优化中的技术调研（陆上风电场）

## 1. 背景

陆上风电场（Onshore Wind Farm）优化已经逐渐从单纯的：

- 风机布局（layout optimization）
- 尾流优化（wake optimization）

扩展到：

- 集电线路优化（electrical collection system）
- 升压站选址
- 多目标经济性优化
- GIS约束
- Terrain-aware routing

其中：

- TOPFARM 负责风场级多学科优化（MDO）
- OptiWindNet 负责集电网络优化

是目前开源生态中较成熟的一套组合。

---

# 2. TOPFARM 与 OptiWindNet 的角色

## 2.1 TOPFARM

TOPFARM 是 DTU 开发的风场级优化框架。

主要能力：

- 风机布局优化
- Wake/AEP 优化
- 多目标优化
- 成本/LCOE优化
- OpenMDAO耦合
- 自定义约束
- 多学科优化（MDO）

适合：

- 陆上风场
- 海上风场
- 多目标工程优化

官方文档：

https://topfarm.pages.windenergy.dtu.dk/TopFarm2/

---

## 2.2 OptiWindNet

OptiWindNet 是 DTU 开发的电气集电网络优化工具。

主要能力：

- 集电线路拓扑优化
- 电缆routing
- feeder assignment
- cable sizing
- no-crossing routing
- 多升压站支持
- 与TOPFARM耦合

官方文档：

https://optiwindnet.readthedocs.io/

---

# 3. 是否可以用于陆上风电场？

结论：

> 可以，而且适合。

但需要区分：

## 3.1 不考虑复杂地形时

如果场景接近：

- 平原
- 戈壁
- 盐碱地
- 大面积平坦区域

则：

TOPFARM + OptiWindNet 基本可以直接使用。

通常无需重大扩展。

因为此时：

    电缆长度 ≈ 电缆成本

欧氏距离近似成立。

---

## 3.2 山地/复杂地形场景

如果存在：

- 山地
- 森林
- 河流 crossing
- 道路约束
- 坡度限制

则需要：

- GIS扩展
- Terrain-aware routing
- Raster cost routing

否则优化结果工程意义有限。

---

# 4. 当前官方已经支持的能力

## 4.1 已有能力

| 功能 | 是否支持 |
|---|---|
| 风机布局优化 | 支持 |
| Wake优化 | 支持 |
| 集电网络拓扑 | 支持 |
| 电缆routing | 支持 |
| cable sizing | 支持 |
| no-crossing routing | 支持 |
| 多升压站 | 支持 |
| polygon boundary | 支持 |
| obstacle avoidance | 支持 |
| TOPFARM耦合 | 支持 |

---

## 4.2 官方示例

官方 notebook：

https://optiwindnet.readthedocs.io/stable/notebooks/c01_Simple_Topfarm_optiwindnet.html

已经实现：

- turbine layout
- electrical routing
- AEP
- cable cost
- economic optimization

---

# 5. 当前缺失的能力

目前开源生态里：

真正缺的是：

    terrain-aware electrical routing

原因：

海上风电默认：

- 海床可通行
- routing近似连续

而陆上风场是：

    GIS + graph optimization 问题

因此：

| 功能 | 当前状态 |
|---|---|
| DEM-aware routing | 缺失 |
| raster least-cost path | 缺失 |
| 山地 turnkey example | 缺失 |
| 道路联合优化 | 缺失 |
| EPC级工程routing | 缺失 |

---

# 6. 推荐的 GIS 扩展方案

## 6.1 推荐架构

建议：

    DEM + LandCover + Roads + Rivers
            ↓
    GIS rasterization
            ↓
    cost surface
            ↓
    A* / Dijkstra / Fast Marching
            ↓
    candidate cable corridors
            ↓
    OptiWindNet topology optimization
            ↓
    TOPFARM outer-loop optimization

---

## 6.2 Cost Raster

典型 cost raster：

| 地形 | Cost |
|---|---|
| 平地 | 1 |
| 林地 | 5 |
| 岩石 | 20 |
| 河流 crossing | 100 |
| 禁建区 | inf |

---

## 6.3 推荐 GIS 工具链

| 工具 | 作用 |
|---|---|
| GeoPandas | GIS vector |
| Rasterio | DEM/raster |
| Shapely | geometry |
| NetworkX | graph routing |
| QGIS | preprocessing |
| RichDEM | terrain analysis |

---

# 7. 升压站（Substation）优化能力分析

## 7.1 当前已经支持的内容

OptiWindNet 已支持：

- 多升压站 routing
- turbine assignment
- feeder optimization
- 多substation topology

例如：

    substationsC = [
        (x1, y1),
        (x2, y2)
    ]

---

## 7.2 当前本质

目前：

    substationsC

本质上是：

    固定坐标输入

不是：

    连续优化变量

因此：

当前更偏：

    给定升压站位置
    → 优化集电网络

而不是：

    自动寻找最佳升压站位置

---

# 8. 多候选升压站优化

## 8.1 这是目前最推荐的工程方案

例如：

候选站点：

- A
- B
- C
- D

然后：

- 自动选择最佳一个/多个
- 比较 cable cost
- 比较 losses
- 比较 LCOE

---

## 8.2 推荐方法

### 方法：外层枚举/离散优化

例如：

    [A]
    [B]
    [C]
    [A,B]
    [A,C]

每组：

- 运行 OptiWindNet
- 计算 objective
- 比较结果

---

## 8.3 为什么工程上更合理

因为真实升压站：

不是连续空间问题。

而是：

- 土地许可
- 高压接入点
- 道路
- 地役权
- 环评

决定的离散问题。

因此：

    candidate-site optimization

比：

    continuous optimization

更工程化。

---

# 9. 是否可以做连续升压站优化？

## 9.1 可以，但不是原生支持

理论上：

可以把：

    substation x,y

作为：

    TOPFARM design variables

实现：

- polygon内自由搜索
- 连续坐标优化

---

## 9.2 推荐架构

推荐：

    TOPFARM
        ├── turbine x,y
        ├── substation x,y
        └── objective

    OptiWindNet
        └── electrical routing

---

## 9.3 约束方式

### 矩形约束

    xmin <= ss_x <= xmax

### polygon约束

使用：

- shapely
- point-in-polygon
- signed distance

---

# 10. 推荐的工程路线

## 第一阶段

直接官方：

    TOPFARM
    + PyWake
    + OptiWindNet

实现：

- layout
- wake
- cable
- economics

---

## 第二阶段

加入：

    polygon obstacles

例如：

- 村庄 buffer
- 湖泊
- 禁建区

---

## 第三阶段

加入：

    terrain-aware routing

包括：

- DEM
- slope cost
- least-cost path

---

# 11. 推荐的整体技术栈

推荐：

    TOPFARM
      + PyWake
      + OptiWindNet
      + GeoPandas
      + Rasterio
      + NetworkX
      + QGIS

---

# 12. 其他值得关注的开源项目

## 12.1 PyWake

GitHub：

https://github.com/DTUWindEnergy/PyWake

能力：

- wake modeling
- AEP
- layout optimization coupling

特点：

- 与TOPFARM天然兼容
- DTU官方生态

---

## 12.2 FLORIS

GitHub：

https://github.com/NREL/floris

机构：

NREL

能力：

- 高级wake建模
- wake steering
- layout optimization

特点：

- 工业界使用广泛
- 可替代部分PyWake能力

---

## 12.3 OpenOA

GitHub：

https://github.com/NREL/OpenOA

能力：

- 风场运行分析
- AEP评估
- operational analytics

特点：

- 更偏运营分析
- 不侧重routing

---

## 12.4 WindSE

GitHub：

https://github.com/NREL/WindSE

能力：

- CFD级风场模拟
- terrain-aware flow

特点：

- 高精度
- 适合复杂地形研究

---

## 12.5 WISDEM

GitHub：

https://github.com/WISDEM/WISDEM

机构：

NREL

能力：

- 风电系统级优化
- turbine + BOS + economics

特点：

- OpenMDAO生态
- 与TOPFARM理念接近

---

## 12.6 OpenWind

项目：

https://github.com/open-wind/openwind

能力：

- GIS preprocessing
- siting
- exclusion zones

特点：

- 非常适合作为GIS前端
- 可与TOPFARM组合

---

## 12.7 pandapower

GitHub：

https://github.com/e2nIEE/pandapower

能力：

- 配电网潮流
- 电气分析
- losses calculation

特点：

- 可用于更真实的电气模型
- 可扩展到集电系统

---

# 13. 当前开源生态的现实情况

当前：

    风场优化框架很多
    GIS工具很多
    但 terrain-aware electrical routing 很少

真正成熟的：

    Onshore GIS-aware wind farm optimization

目前仍是：

- 研究热点
- 工程空白
- 很有产品价值的方向

---

# 14. 最终结论

## 14.1 如果不考虑复杂地形

则：

TOPFARM + OptiWindNet：

已经足够用于：

- 陆上风场layout
- wake optimization
- electrical optimization
- economic optimization

无需重大扩展。

---

## 14.2 如果考虑复杂地形

则建议加入：

- GIS
- cost raster
- terrain-aware routing
- least-cost path

否则：

线路优化工程意义有限。

---

## 14.3 关于升压站

当前最合理路线：

    candidate substations
        +
    TOPFARM outer optimization
        +
    OptiWindNet routing

而不是：

    完全连续自由选址

因为：

真实工程本身是：

    离散站点优化问题。

