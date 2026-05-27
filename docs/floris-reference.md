# FLORIS 工程师详细版技术参考

## 1. 文档定位

本文由以下三份材料合并整理而成：

- `wind/docs/floris-reference.md`
- `wind/docs/floris-reference-ai-v1.md`
- `wind/docs/floris-reference.docx`

整理目标是形成一份兼顾两类读者的统一参考材料：

- 面向工程师：快速理解 FLORIS 的技术架构、模型体系、优化方法、适用场景与代码入口；
- 面向市场与投标人员：可直接提炼 FLORIS 的技术优势、产品特点、方案亮点与宣传表达。

因此，本文采用“双层结构”：

- 前半部分强调 FLORIS 的价值定位、技术优势与方案亮点，适合汇报、投标和对外材料引用；
- 后半部分展开到工程师详细版，适合作为技术学习、方案设计和二次开发的参考材料。

## 2. 执行摘要

FLORIS（FLOw Redirection and Induction in Steady State）是一套面向风电场控制、性能评估与工程优化的工程尾流建模框架。它不是以全三维高保真 CFD 为核心的重型求解器，而是围绕稳态尾流机理构建的一套模块化、可解释、可扩展、适合工程快速迭代的 Python 平台。

对于风电行业而言，FLORIS 的价值不只在于“能算尾流”，更在于它把风场仿真、控制优化、布局评估、不确定性分析和多场景批量计算连接成了一个完整的工程闭环。与传统只做静态功率评估的工具相比，FLORIS 更强调“从模型到控制、从单工况到多工况、从风机级到风场级”的统一分析能力。

从项目应用的角度，可以将 FLORIS 理解为一种兼顾精度、速度和可部署性的工程技术底座。它特别适合以下任务：

- 风电场年发电量与尾流损失评估；
- 风机布局比较与场址方案筛选；
- 偏航控制与协同控制策略研究；
- 复杂风况、异质来流与参数不确定性下的稳健性分析；
- 面向投标、可研、技术路线论证的方案支撑材料输出。

## 3. 市场化价值与宣传要点

### 3.1 为什么 FLORIS 值得重点关注

在风电场优化问题中，行业通常面临三类典型挑战：

- 尾流模型过于粗糙，导致功率预测和尾流损失评估偏差较大；
- 仿真模型与控制执行脱节，难以支持偏航优化、降额控制等实际应用；
- 复杂地形、异质来流和多工况分析成本高，难以快速支撑工程决策。

FLORIS 的市场吸引力，正来自于它对这些问题的系统回应。它不是把风电场看成“单机功率曲线的简单叠加”，而是将尾流速度亏损、尾流偏转、湍流增长、尾流叠加、控制变量和优化目标整合进一个统一框架中，从而让风电场分析从“静态估算”升级为“面向控制和优化的工程计算平台”。

### 3.2 可用于投标与汇报的核心卖点

从市场与方案包装角度，可以将 FLORIS 的优势概括为以下几点：

- 模块化工程尾流建模平台。支持多类速度亏损、偏转、湍流和叠加模型灵活组合，适应不同项目阶段对速度与精度的要求。
- 控制导向的分析能力。能够将尾流仿真与偏航优化、功率设定、载荷优化等控制任务打通，形成从仿真到策略评估的闭环。
- 高效批量计算能力。支持并行风况计算、参数扫描、不确定性分析和快速近似评估，适合大规模风况表和多方案对比。
- 支持复杂工程场景。可处理异质来流、多维 `Cp/Ct` 性能曲面、浮式风机场景以及复杂边界与布局约束。
- 兼顾研究与工程。既可支撑技术研究和算法验证，也便于形成项目级分析结论、汇报材料和投标支撑内容。

### 3.3 宣传表达建议

在对外材料中，可以参考以下表述方式：

- FLORIS 是一套面向风电场控制优化的先进工程尾流建模平台，可支撑从风场仿真、尾流评估到控制优化和稳健性分析的全流程应用。
- FLORIS 通过模块化尾流模型体系，将速度亏损、尾流偏转、湍流演化与尾流叠加统一建模，为风电场精细化评估和控制策略设计提供高效支撑。
- 相比仅用于静态发电量估算的传统工具，FLORIS 更适合面向风场级协同控制、布局优化和多场景快速评估的工程需求。
- FLORIS 兼顾物理机理、工程计算效率与优化应用接口，适合作为风电场数字化分析和控制策略研究的技术底座。

### 3.4 宣传材料使用边界

`floris-reference.docx` 中包含部分市场化表达、案例化描述和效果型措辞。为了兼顾宣传效果与技术严谨性，本文保留其叙事风格与价值导向，但未直接保留其中未经本仓库代码或官方文档明确支撑的定量结论。若后续用于正式投标、白皮书或客户材料，建议将所有具体性能数字替换为项目实测数据、论文结果或客户案例数据。

## 4. FLORIS 的技术定位

### 4.1 FLORIS 是什么

FLORIS 是一套围绕稳态尾流模型构建的风电场分析框架。它的定位不是高保真 CFD 求解器，而是一个以工程效率为优先、同时保持物理可解释性的中低保真风场建模平台。

如果用一句话概括 FLORIS 的技术价值，可以理解为：

FLORIS 在“物理可解释性”和“工程可优化性”之间找到了一个实用平衡点，特别适合用于风电场级别的方案比较、控制策略研究和参数敏感性分析。

### 4.2 与传统工具相比的特点

从工程使用角度看，FLORIS 有几个很突出的特征：

- 模块化。尾流模型被拆分为速度亏损、尾流偏转、湍流、尾流叠加四个子模块，可以按场景组合。
- 面向控制。除了静态布局评估，它也直接支持偏航优化、功率设定优化、载荷优化和价值函数评估。
- 适合批量评估。通过 `ParallelFlorisModel`、`ApproxFlorisModel` 和 `UncertainFlorisModel`，可以面向风况集合、参数不确定性和快速扫描做高效率计算。
- 支持工程扩展。官方实现已经覆盖浮式风机、异质来流、多维 `Cp/Ct` 曲线、复杂边界、价值函数与优化器接口等高级主题。

### 4.3 适合解决哪些问题

FLORIS 特别适合以下类型的问题：

- 机组间尾流损失分析；
- 风电场功率分布与流场可视化分析；
- 风场布局优化与边界约束下的方案比较；
- 偏航控制、降额控制和价值导向控制研究；
- 大量风况工况组合下的 AEP 计算；
- 异质来流、复杂边界和浮式平台影响评估；
- 参数敏感性分析、稳健性分析和不确定性量化。

## 5. 核心能力与代码结构

FLORIS 的优势不只体现在单个尾流公式上，更体现在一套完整的“建模-评估-优化-分析”流程中。结合当前仓库结构，可以将其能力概括为以下几类。

### 5.1 尾流建模

FLORIS 集成了多种工程尾流模型，用于模拟风机之间的尾流相互作用。常见实现位于：

- `floris/core/wake_velocity/`
- `floris/core/wake_deflection/`
- `floris/core/wake_turbulence/`
- `floris/core/wake_combination/`

用户可以根据场景选择不同的速度亏损模型、偏转模型、湍流模型和叠加方法，从而在计算速度与模型精细度之间折中。

### 5.2 优化与控制

FLORIS 的优化模块支持从静态设计到动态控制的多类任务，主要包括：

- 偏航优化：`floris/optimization/yaw_optimization/`
- 布局优化：`floris/optimization/layout_optimization/`
- 载荷优化：`floris/optimization/load_optimization/`
- 控制相关机组运行模型：`floris/core/turbine/controller_dependent_operation_model.py`

这意味着 FLORIS 不只是一个“算尾流”的工具，也能把尾流模型直接嵌入工程决策闭环中。

### 5.3 并行评估、近似模型与不确定性分析

当工况数量增多时，模型运行成本往往不在单次仿真，而在风况矩阵、参数扫描和稳健性分析。FLORIS 提供了相应能力：

- 并行评估：`floris/par_floris_model.py`
- 近似模型示例：`examples/examples_uncertain/002_approx_floris_model.py`
- 不确定性建模：`floris/uncertain_floris_model.py`
- 异质来流映射：`floris/heterogeneous_map.py`

这类工具通常用于大规模 AEP 评估、输入扰动分析、模型参数敏感性研究，以及复杂风场背景下的工程方案比较。

### 5.4 可视化与示例

FLORIS 提供了用于流场和结果展示的可视化工具：

- `floris/flow_visualization.py`

此外，仓库中的示例目录对理解高级场景很有帮助，例如：

- 浮式风机示例：`examples/examples_floating/`
- 多维 `Cp/Ct` 示例：`examples/examples_multidim/`
- 布局优化示例：`examples/examples_layout_optimization/`
- 载荷优化示例：`examples/examples_load_optimization/`

## 6. 尾流模型体系

### 6.1 什么是尾流模型

当上游风机从来流中提取能量后，下游会形成一个风速降低、湍流增强、速度分布不均匀的流动区域，这个区域就是尾流（wake）。尾流会降低下游风机可获得的风速，并改变其入流条件，因此直接影响风场总发电量与载荷。

在 FLORIS 中，一个完整的尾流模型通常由四部分组成：

1. 速度亏损模型（wake velocity model）
   描述尾流区内风速相对自由流降低了多少，以及这种亏损如何沿下游扩张和衰减。
2. 尾流偏转模型（wake deflection model）
   描述偏航失配后，尾流中心线如何横向或垂向偏移。
3. 湍流模型（wake turbulence model）
   描述尾流诱导湍流如何增长，并反馈到尾流恢复过程。
4. 尾流叠加模型（wake combination model）
   当多台上游风机同时影响同一位置时，定义多个尾流如何合成为总的速度亏损。

从建模思路上看，FLORIS 不是把风场当成黑箱，而是把“尾流的形成、偏移、恢复、叠加”拆成可替换的组件。这样做的好处是，工程师可以根据精度、速度和工况特点选择不同的模型组合。

### 6.2 速度亏损模型

#### 6.2.1 Jensen 模型

对应实现：`floris/core/wake_velocity/jensen.py`

Jensen 模型也常被称为 Park 模型，是经典的工程尾流模型之一。它把尾流近似为一个随下游距离线性扩张的“顶帽型”区域：尾流内部速度亏损近似均匀，尾流外部近似等于自由流。

其典型表达式可写成：

$$
\Delta U(x) = U_\infty \left(1-\sqrt{1-\frac{C_T}{(1+2kx/D)^2}}\right)
$$

其中：

- $U_\infty$ 是自由流风速；
- $C_T$ 是推力系数；
- $D$ 是转子直径；
- $x$ 是下游距离；
- $k$ 是尾流扩张系数。

核心特点包括：

- 采用顶帽型亏损分布；
- 尾流半径随下游距离线性扩张；
- 计算效率高，适合大规模快速筛选；
- 对横向分布和近尾流细节表达较粗。

Jensen 模型的工程优点是速度快、稳健、参数少，适合做初步布局规划和大范围方案扫描；局限则在于对偏航控制和细粒度尾流结构的表达能力较弱。

#### 6.2.2 Gauss 模型

对应实现：`floris/core/wake_velocity/gauss.py`

Gauss 模型用高斯分布描述尾流截面上的速度亏损，是 FLORIS 中非常核心的一类模型。与 Jensen 的“整块一起减速”不同，Gauss 模型认为尾流中心亏损最大，往边缘平滑衰减，更贴近真实尾流的横向分布特征。

典型形式可写为：

$$
\frac{\Delta U}{U_\infty}
=
C(x)\exp\left(
-\frac{(y-\delta)^2}{2\sigma_y^2}
-\frac{(z-z_h)^2}{2\sigma_z^2}
\right)
$$

其中：

- $C(x)$ 表示沿下游方向变化的中心亏损强度；
- $\delta$ 是尾流偏转量；
- $\sigma_y,\sigma_z$ 分别是横向和垂向尾流宽度；
- $z_h$ 是轮毂高度。

Gauss 模型的工程特点包括：

- 尾流截面分布更加平滑；
- 更适合分析尾流偏转和尾流重叠；
- 更适合研究偏航控制和非均匀来流响应；
- 相比 Jensen，计算成本略高但物理表达更细致。

#### 6.2.3 Empirical Gauss 模型

对应实现：`floris/core/wake_velocity/empirical_gauss.py`

Empirical Gauss 可以理解为在高斯尾流框架上加入经验修正，使模型更适合工程校准和特定数据集上的表现。它保留了高斯分布的主要结构，但会对尾流扩张、近尾流到远尾流的过渡、偏转与恢复行为做经验参数化处理。

其核心形式仍然类似：

$$
\frac{\Delta U}{U_\infty}
\propto
\exp\left(
-\frac{(y-\delta)^2}{2\sigma_y^2}
-\frac{(z-z_h)^2}{2\sigma_z^2}
\right)
$$

Empirical Gauss 的价值在于：

- 保留高斯模型的物理结构；
- 为经验调参和项目校准留出空间；
- 更适合结合实测数据或特定风场经验做修正。

#### 6.2.4 Cumulative Gauss Curl 模型

对应实现：`floris/core/wake_velocity/cumulative_gauss_curl.py`

Cumulative Gauss Curl 模型是在高斯尾流基础上进一步增强对旋转、偏航和尾流卷吸效应的表达能力。它常用于更细致地模拟偏航偏置后尾流的弯曲和速度分布变化。

其主要特点是：

- 用高斯型亏损表示主尾流；
- 通过附加的 curl 或 rotation 相关项增强横向速度结构；
- 更强调偏航诱导偏转与卷吸效应的累计影响。

如果项目重点是偏航控制研究、尾流弯曲形态分析或更复杂的横向流动结构描述，这类模型通常更有参考价值。

#### 6.2.5 TurbOPark / TurbOParkGauss 模型

对应实现：

- `floris/core/wake_velocity/turbopark.py`
- `floris/core/wake_velocity/turboparkgauss.py`

TurbOPark 系列模型主要面向大尺度风电场尾流相互作用，尤其适合需要描述长距离尾流恢复、风场整体尾流背景效应的情形。

这类模型的工程特点是：

- 强调大风场尺度下的尾流扩张与恢复；
- 对风场整体相互作用的处理更系统；
- 更适合用于海上大型风电场或长列阵风机情形。

可以把它理解为“更偏风场尺度”的尾流模型族。

### 6.3 偏转模型

官方文档和代码中常见的偏转模型包括：

- Jimenez 模型：`floris/core/wake_deflection/jimenez.py`
- Gauss 偏转模型：`floris/core/wake_deflection/gauss.py`
- Empirical Gauss 偏转模型：`floris/core/wake_deflection/empirical_gauss.py`
- None：`floris/core/wake_deflection/none.py`

这些模型的共同目标是计算尾流中心线偏移量 $\delta(x)$。在工程上可以把它理解为：

$$
\delta(x)=f(x,\gamma,C_T,TI,\ldots)
$$

其中 $\gamma$ 为偏航角，$TI$ 为湍流强度。偏航角越大，尾流通常偏得越明显，但偏转量还会受到推力系数、湍流和下游恢复过程的共同影响。

### 6.4 湍流模型

FLORIS 中常见的尾流湍流模型包括：

- Crespo-Hernandez：`floris/core/wake_turbulence/crespo_hernandez.py`
- Wake-induced mixing：`floris/core/wake_turbulence/wake_induced_mixing.py`
- None：`floris/core/wake_turbulence/none.py`

它们的任务是估算尾流附加湍流强度，并将其反馈给尾流扩张和恢复过程。常见工程表达可写成：

$$
TI_{\mathrm{wake}} = f(a,TI_\infty,x/D)
$$

其中 $a$ 为轴向诱导因子，$TI_\infty$ 为环境湍流强度。直观上，尾流湍流越强，混合越快，尾流恢复也越快。

### 6.5 尾流叠加模型

当多股尾流同时作用于同一台下游风机时，需要定义总亏损如何计算。FLORIS 常见的叠加方式包括：

- FLS：`floris/core/wake_combination/fls.py`
- SOSFS：`floris/core/wake_combination/sosfs.py`
- MAX：`floris/core/wake_combination/max.py`

其中常见的工程思路是平方和叠加，例如：

$$
\Delta U_{\mathrm{tot}} =
\sqrt{\sum_i (\Delta U_i)^2}
$$

这种做法比简单线性叠加更稳健，不容易高估多重尾流造成的总亏损。

### 6.6 如何选择尾流模型

尾流模型的选型通常取决于精度要求、计算预算和场景特征，而不是简单地“一种模型适合某种地形”。较实用的判断方式是：

- 需要快速做大规模方案筛选时，可优先考虑 Jensen 这类低成本模型；
- 需要更细致地分析尾流横向分布、偏航控制和尾流重叠时，通常更适合选用 Gauss 或 Empirical Gauss；
- 对大型风电场、长距离尾流和整体风场背景效应更敏感的研究，可考虑 TurbOPark 或 TurbOParkGauss；
- 对偏航诱导旋转结构和更复杂尾流形态特别关注时，可进一步考虑 Cumulative Gauss Curl。

工程上更可靠的做法通常不是先问“哪种模型最好”，而是先明确目标问题，再用统一风况集对多个模型做对比评估。

## 7. 优化与控制算法

FLORIS 的优化模块并不是单一优化器，而是一组围绕不同决策变量构建的优化工具。按工程用途，可分为偏航优化、布局优化和功率或载荷相关优化。

### 7.1 偏航优化

偏航优化的目标是通过主动让上游风机偏离正对来流的方向，换取整个风场总发电量提升。其基本逻辑是：上游风机单机可能略损失功率，但尾流被偏开后，下游风机获得更高来流，风场总收益可能增加。

FLORIS 中常见的偏航优化器包括：

- `YawOptimizationGeometric`
- `YawOptimizerSR`
- `YawOptimizationScipy`

#### 7.1.1 Geometric 方法

对应实现：`floris/optimization/yaw_optimization/yaw_optimizer_geometric.py`

几何法利用风机相对位置和来流方向快速判断“哪些机组值得偏航、偏多少更合理”，属于启发式方法。它不追求每一步都做严格数值最优，而是用几何关系快速构造一个较优偏航解。

优点是速度快、适合大规模风况表或在线近实时应用；缺点是全局最优性通常不如通用数值优化器。

#### 7.1.2 SR 方法

`YawOptimizerSR` 中的 SR 一般指 Serial Refine。它的核心思想是：

1. 先在较粗的搜索网格上逐台或逐组扫描偏航角；
2. 找到较优区域后缩小范围；
3. 重复细化，逐步逼近更优解。

这种方法兼顾了鲁棒性和效率，特别适合变量维度不算太高、但又希望比纯启发式更稳的场景。

#### 7.1.3 Scipy 数值优化

`YawOptimizationScipy` 使用 SciPy 提供的通用优化器，把总功率最大化问题写成一个带边界约束的非线性优化问题。数学上可以表示为：

$$
\max_{\gamma_1,\ldots,\gamma_N} \; P_{\mathrm{farm}}(\gamma_1,\ldots,\gamma_N)
$$

subject to

$$
\gamma_i^{\min}\le \gamma_i \le \gamma_i^{\max}
$$

其优点是形式清晰、便于加入约束；缺点是计算量通常高于几何法和串行细化法。

### 7.2 布局优化

布局优化的目标是在场址约束下寻找更优的风机坐标。典型决策变量是每台风机的平面位置 $(x_i,y_i)$，目标函数通常是 AEP、某种价值函数，或附加了成本和约束惩罚项的综合指标。

典型形式可以写成：

$$
\max_{\{x_i,y_i\}} \; \mathrm{AEP}(\{x_i,y_i\})
$$

subject to

$$
(x_i,y_i)\in \Omega,\quad
d_{ij}\ge d_{\min}
$$

其中 $\Omega$ 表示场址边界或可布机区域，$d_{ij}$ 是风机间距。

仓库中可见的布局优化实现主要包括：

- `floris/optimization/layout_optimization/layout_optimization_scipy.py`
- `floris/optimization/layout_optimization/layout_optimization_random_search.py`
- `floris/optimization/layout_optimization/layout_optimization_gridded.py`
- `floris/optimization/layout_optimization/layout_optimization_boundary_grid.py`
- `floris/optimization/layout_optimization/layout_optimization_pyoptsparse.py`
- `floris/optimization/layout_optimization/layout_optimization_pyoptsparse_spread.py`

相应示例包括：

- `examples/examples_layout_optimization/001_optimize_layout.py`
- `examples/examples_layout_optimization/002_optimize_layout_with_heterogeneity.py`
- `examples/examples_layout_optimization/003_genetic_random_search.py`
- `examples/examples_layout_optimization/004_generate_gridded_layout.py`
- `examples/examples_layout_optimization/005_layout_optimization_complex_boundary.py`

这类方法的共同点是：把风场能量评估嵌入数值优化器，每次迭代调用 FLORIS 重新计算风场功率或 AEP。若风况离散较多，布局优化通常比偏航优化更耗时，因此常结合并行计算或快速近似模型。

### 7.3 功率设定与载荷相关优化

除了偏航和布局，FLORIS 还支持基于功率设定点或控制器相关变量的优化，这类问题常用于研究降额运行、负载缓释或价值导向控制。

相关实现位于：

- `floris/optimization/load_optimization/load_optimization.py`

相关示例包括：

- `examples/examples_load_optimization/001_lti_and_voc.py`
- `examples/examples_load_optimization/002_row_opt_example.py`

其一般形式可写为：

$$
\max_{\mathbf{u}} \; J(\mathbf{u})
$$

其中 $\mathbf{u}$ 可为功率设定、轴向诱导相关控制量等，$J$ 可以是总发电量、收益、载荷代理指标或二者加权组合。

工程上，这类优化常见两种思路：

- 直接把功率或价值函数作为目标，寻找最优控制量；
- 在满足总功率、单机上限或载荷约束前提下，做约束优化。

### 7.4 工程求解建议

对于真实工程问题，通常更适合按以下顺序使用优化工具：

1. 先用 `FlorisModel` 做基准工况评估；
2. 再用几何法、串行细化法或快速布局方法做初步搜索；
3. 对候选方案用更细的风况表和更精细的模型重新计算；
4. 结合 `ParallelFlorisModel` 或近似模型提升批量分析效率；
5. 最后再引入不确定性分析或价值函数比较方案稳健性。

这样做的好处是，不会把某个局部工况下的最优解误认为工程上最优解。

## 8. 复杂工程场景

### 8.1 浮式风电场

FLORIS 官方示例中已包含浮式风机相关内容，对应目录为：

- `examples/examples_floating/001_floating_turbine_models.py`
- `examples/examples_floating/002_floating_vs_fixedbottom_farm.py`
- `examples/examples_floating/003_tilt_driven_vertical_wake_deflection.py`

对于浮式风机，难点在于风机并不是固定在刚性地基上，而是会随平台产生俯仰、横摇、纵摇或位置变化，从而改变转子相对来流的姿态。

在 FLORIS 的工程处理思路中，可以把这类影响理解为以下几类修正：

- 风机姿态改变：等效改变轮毂位置、转子法向和入流夹角；
- 偏航与倾斜耦合：平台运动会改变尾流偏转与尾流中心线位置；
- 多工况评估：通过工况样本或不确定性建模评估平台运动对年发电量和控制收益的影响。

需要强调的是，FLORIS 对浮式场景的处理仍属于工程级尾流建模，不等同于把浮体水动力、系泊动力学和高保真气动弹性全过程直接求解出来。

### 8.2 异质来流与复杂地形近似

官方文档对这一主题更直接的表述通常是 heterogeneous inflow 或 heterogeneous map，而不是完整意义上的三维地形流 CFD。换句话说，FLORIS 更擅长处理“空间上不均匀的来流场”，例如：

- 山脊或坡地造成的局部风速增减；
- 海陆过渡带导致的流场不均匀；
- 场内不同区域存在不同风速放大系数；
- 局部测风或中尺度模型结果被映射为风场内的空间分布。

其工程做法是为风场提供一个空间变化的来流修正场，再由尾流模型在该非均匀背景风场上继续计算机组间相互作用。可以理解为：

$$
U_\infty \rightarrow U_\infty(x,y,z)
$$

然后再叠加尾流亏损：

$$
U(x,y,z)=U_\infty(x,y,z)-\Delta U_{\mathrm{wake}}(x,y,z)
$$

因此，若把“复杂地形条件”理解为“地形造成的非均匀来流”，FLORIS 是可以处理的；若理解为“直接求解复杂地形绕流的三维流场”，则通常需要借助更高保真的外部模型，再把结果映射回 FLORIS。

### 8.3 多目标与复杂约束优化

结合布局优化、载荷优化和外部优化接口，FLORIS 可以支持更复杂的目标组合，例如：

- 发电量最大化与载荷最小化之间的权衡；
- 边界、多边形禁布区和最小间距约束下的布局设计；
- 异质来流条件下的稳健布局优化；
- 面向收益而非单纯发电量的价值函数优化。

因此，FLORIS 特别适合承担“技术论证平台”角色，用于在多个方案之间快速构建可比较、可解释的工程指标。

### 8.4 不确定性量化与稳健性分析

相关实现：`floris/uncertain_floris_model.py`

在真实风场中，风速波动、风向误差、湍流变化和模型参数不确定性都会影响优化结果的可用性。`UncertainFlorisModel` 的价值在于：它能把“单一确定工况”扩展成“带概率扰动的一组工况”，从而评估方案的期望收益和波动范围。

这类分析通常可以用于：

- 参数敏感性分析；
- 控制策略稳健性评估；
- 不同尾流模型下结果波动比较；
- 年发电量或收益结果的区间化表达。

## 9. 多维参数分析与高级能力

### 9.1 可分析的关键维度

常见的分析维度包括：

- 风速；
- 风向；
- 湍流强度；
- 空气密度；
- 风机 `Cp/Ct` 曲线或多维性能曲面；
- 偏航角、功率设定值等控制变量；
- 布局参数，如间距、排布角度、边界约束；
- 异质来流参数。

这些维度既可以单独扫描，也可以联合构成风况矩阵。

### 9.2 在布局优化中的参数评估

布局优化里常见的问题是：某个布局是只对单一主导风向有效，还是对整个风玫瑰都有效。FLORIS 中常见的评估方式包括：

1. AEP 评估
   用一组离散风速、风向频率计算全年加权发电量。
2. 稳健性评估
   比较布局在不同湍流强度、不同模型参数、不同来流不确定性下的性能变化。
3. 价值函数评估
   不只看发电量，也看收益、削峰、功率跟踪等更复杂指标。

若从方法论上写，可以把布局性能看成：

$$
\mathrm{Score}=\sum_{m} w_m \, J_m(\{x_i,y_i\},\theta_m)
$$

其中 $m$ 表示不同工况，$w_m$ 为工况权重，$\theta_m$ 为该工况下的环境参数。

### 9.3 在控制优化中的参数评估

控制优化，尤其是偏航优化，不应只看单一工况的“最优偏航角”，还要看以下问题：

- 对风向偏差是否敏感；
- 对湍流强度变化是否敏感；
- 对尾流模型切换是否稳健；
- 在多台机组同时控制时是否容易过拟合某一类工况。

这时可以结合 `UncertainFlorisModel` 做输入扰动，把某个确定工况扩展成一个概率分布下的工况集合，再比较控制策略的期望收益和波动范围。

### 9.4 多维 `Cp/Ct` 与性能曲面

多维 `Cp/Ct` 的意义在于：风机性能不必只是一条“风速-功率曲线”，还可以是多输入维度下的性能面，例如与湍流、控制状态或运行模式耦合的 `Cp/Ct` 数据。

这使得以下分析成为可能：

- 同一控制策略在不同运行状态下的性能差异；
- 某些降额策略对推力和尾流恢复的影响；
- 风机机型或控制模式变化对风场优化结果的传递影响。

仓库中对应的示例包括：

- `examples/examples_multidim/001_multi_dimensional_cp_ct.py`
- `examples/examples_multidim/002_multi_dimensional_cp_ct_2Hs.py`
- `examples/examples_multidim/003_multi_dimensional_cp_ct_TI.py`
- `examples/inputs/gch_multi_dim_cp_ct.yaml`
- `examples/inputs/gch_multi_dim_cp_ct_TI.yaml`

示例代码：

```python
from floris import FlorisModel

fmodel = FlorisModel("examples/inputs/gch_multi_dim_cp_ct.yaml")

fmodel.set(
    wind_directions=[270, 280, 290],
    wind_speeds=[8.0, 9.0, 10.0],
    turbulence_intensities=[0.06, 0.07, 0.08],
)

fmodel.run()
power = fmodel.get_turbine_powers()
```

### 9.5 推荐的工程分析流程

对于布局或控制优化，比较推荐的 FLORIS 使用流程是：

1. 先用 `FlorisModel` 或 `ParallelFlorisModel` 做基准工况评估；
2. 用快速优化器或近似模型做大范围参数扫描；
3. 对候选方案用更细的风况表重新计算；
4. 用 `UncertainFlorisModel` 做稳健性分析；
5. 用价值函数比较“高发电量”与“高收益或高稳健性”之间的差异。

这样做的好处是，不会把“某个工况下的最优”误认为“全年最优”或“工程上最优”。

## 10. 面向投标与方案输出的建议写法

如果要把 FLORIS 用于项目建议书、投标文件、技术路线说明或客户汇报材料，可从以下四个角度组织内容：

- 技术先进性：强调其模块化尾流模型体系、控制导向能力、多场景评估能力和复杂工程场景适应能力。
- 工程可实施性：强调其计算效率高、适合快速方案比较、便于结合现有风资源数据和机组参数开展分析。
- 方案可扩展性：强调其支持异质来流、多维性能曲面、复杂边界、浮式场景与多目标优化，适合逐步扩展。
- 决策支撑能力：强调其不仅能给出功率结果，还能支撑控制优化、稳健性分析、敏感性分析和多方案对比。

可直接引用的投标型表述包括：

- 基于 FLORIS 构建的风电场分析平台，可为项目提供从尾流评估、布局优化到控制策略研究的一体化技术支撑。
- 该技术路线兼顾工程计算效率与风场级物理可解释性，适用于项目前期方案比选、技术优化和运行策略评估。
- 平台支持复杂边界、异质来流、多工况批量计算及不确定性分析，能够为项目决策提供更系统的量化依据。

## 11. 参考资料

以下链接均来自 FLORIS 官方文档，适合作为进一步阅读入口：

- FLORIS 首页: https://natlabrockies.github.io/floris/index.html
- Developer guide: https://natlabrockies.github.io/floris/dev_guide.html
- Wake models: https://natlabrockies.github.io/floris/wake_models.html
- FLORIS models: https://natlabrockies.github.io/floris/floris_models.html
- Layout optimization: https://natlabrockies.github.io/floris/layout_optimization.html
- Control optimization examples: https://natlabrockies.github.io/floris/examples_control_optimization.html
- Heterogeneous map: https://natlabrockies.github.io/floris/heterogeneous_map.html
- Multidimensional wind turbine: https://natlabrockies.github.io/floris/multidimensional_wind_turbine.html
- Value functions: https://natlabrockies.github.io/floris/value_functions.html

## 12. 说明

1. 本文由 `wind/docs/floris-reference.md`、`wind/docs/floris-reference-ai-v1.md` 与 `wind/docs/floris-reference.docx` 合并整理而成，并结合当前仓库中的模块路径做了交叉核对。
2. 本文保留了 `docx` 中“技术价值、市场亮点、应用优势、方案卖点”的叙述风格，但对部分未经本地代码或官方文档直接支撑的定量宣传内容做了中性化处理。
3. 对“复杂地形条件”的表述，本文将官方文档中的 heterogeneous inflow 或 heterogeneous map 解释为复杂地形、地表粗糙度变化或局部加减速来流的一种工程近似，这是基于官方文档所做的工程化归纳。
4. 各模型公式在不同论文、版本和实现中可能存在参数定义差异；若需要用于二次开发，应以对应版本的官方实现和原始参考文献为准。
