# 使用 GeoJSON 进行 FLORIS 风电场布局优化

本文档说明如何使用 GeoJSON 地理数据进行 FLORIS 风电场布局优化。

## 📋 文件列表

### 核心脚本

| 文件 | 位置 | 说明 |
|-----|-----|-----|
| `changpin_gridded_layout_optimization.py` | `/wind/` | 🌟 **推荐使用** - 完整的优化示例脚本 |
| `example_usage.py` | `/wind/test/` | 集成示例（含 5 个示例函数） |
| `convert_geojson_for_floris.py` | `/wind/test/` | 坐标转换工具库 |
| `read_geojson_with_qgis.py` | `/wind/test/` | GeoJSON 读取工具库 |

### 数据文件

| 文件 | 位置 | 说明 |
|-----|-----|-----|
| `changpin.geojson` | `/wind/data/` | 昌平区边界数据 |
| `fangshan.geojson` | `/wind/data/` | 房山区边界数据 |
| `beijing.geojson` | `/wind/data/` | 北京市边界数据 |

## 🚀 快速开始

### 方式 1: 运行完整优化脚本（推荐）

```bash
cd /home/frank/opensource/floris/wind
python changpin_gridded_layout_optimization.py
```

**输出内容：**
- ✅ 步骤 1: 加载 GeoJSON 数据
- ✅ 步骤 2: 转换坐标（经纬度 → 投影坐标）
- ✅ 步骤 3: 加载 FLORIS 模型
- ✅ 步骤 4: 配置 Gridded Layout 优化器
- ✅ 步骤 5: 执行优化算法
- ✅ 步骤 6: 分析结果统计
- ✅ 步骤 7: 计算年发电量（AEP）
- ✅ 步骤 8: 导出 JSON 结果
- ✅ 步骤 9: 绘制和保存图表

**输出文件：**
```
./wind/
├── changpin_optimization_results.json     ← 优化结果（JSON 格式）
└── changpin_layout_optimization.png       ← 布局可视化图表
```

### 方式 2: 运行集成示例（学习用）

```bash
cd /home/frank/opensource/floris/wind/test
python example_usage.py
```

**包含 5 个示例：**
1. 基本使用方法
2. 获取特定行政区划范围
3. 按名称查询行政区划
4. 导出边界数据为 JSON
5. **✨ FLORIS Gridded Layout 优化**

## 📊 输出结果解读

### JSON 结果文件（`changpin_optimization_results.json`）

```json
{
  "metadata": {
    "region": "Changpin District (昌平区)",
    "optimization_method": "Gridded Layout"
  },
  "optimization_parameters": {
    "spacing_D": 5.0,                  // 最小间距（风机直径倍数）
    "spacing_meters": 629.4            // 最小间距（米）
  },
  "results": {
    "turbine_count": 42,               // 优化后风机数量
    "aep_total_MWh_per_year": 1234.56, // 总年发电量
    "aep_per_turbine_MWh_per_year": 29.39 // 单机年发电量
  },
  "turbine_locations": [
    {"id": 0, "x_m": 516123.45, "y_m": 3382456.78},
    ...
  ]
}
```

### 图表文件（`changpin_layout_optimization.png`）

显示内容：
- 🔵 蓝点：初始风机位置
- 🔴 红点：优化后风机位置
- ⬛ 边界框：风电场边界（昌平区边界）
- 📏 网格：参考网格

## 🔄 工作流程详解

### 完整流程

```
┌─────────────────────────────────────────────────────────────┐
│  GeoJSON 数据 (经纬度坐标)                                   │
│  changpin.geojson: [[116.499, 40.260], [116.476, 40.244], ...] │
└─────────────────────┬───────────────────────────────────────┘
                      │
        🔄 坐标转换 (GEOJSONToFLORISConverter)
        
┌─────────────────────────────────────────────────────────────┐
│  投影坐标 (UTM, 单位：米)                                    │
│  boundaries: [(500012.45, 3380123.67), (500145.23, ...)]   │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ⚙️  创建 FLORIS 模型 + Gridded Layout 优化器
        
┌─────────────────────────────────────────────────────────────┐
│  FLORIS 布局优化 (LayoutOptimizationGridded)                 │
│  • 旋转和平移网格                                            │
│  • 最大化网格范围内的风机数量                                │
│  • 保持最小间距约束                                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ⚡ 运行 AEP 计算
        
┌─────────────────────────────────────────────────────────────┐
│  优化结果                                                    │
│  • 风机位置列表                                              │
│  • 年发电量 (AEP)                                            │
│  • 布局可视化                                                │
└─────────────────────────────────────────────────────────────┘
```

## 💻 模仿的原始脚本

原始脚本：`examples/examples_layout_optimization/004_generate_gridded_layout.py`

**区别：**

| 项目 | 原始脚本 | 新脚本 |
|-----|--------|--------|
| 边界数据 | 硬编码的 1000m × 1000m 方形 | GeoJSON 真实地理数据 |
| 坐标系 | 本地笛卡尔坐标 | UTM 投影坐标 |
| 风电场规模 | 小型示例 | 真实行政区划 |
| 数据源 | 代码内定义 | 外部 GeoJSON 文件 |

## 🛠️ 自定义使用

### 修改 GeoJSON 数据源

要使用其他数据（如房山区），修改脚本中的：

```python
geojson_file = Path(__file__).parent / "data" / "fangshan.geojson"  # 改为 fangshan
```

### 修改优化参数

```python
layout_opt = LayoutOptimizationGridded(
    fmodel,
    boundaries,
    min_dist_D=6.0,           # 改为 6 倍风机直径
    rotation_step=10.0,       # 改为 10° 步长
    translation_step_D=2.0,   # 改为 2 倍直径步长
    hexagonal_packing=True,   # 改为六边形网格
)
```

### 获取特定特征

如果 GeoJSON 包含多个特征（features），修改索引：

```python
boundaries = converter.get_floris_boundaries(1, auto_crs=True)  # 获取第 2 个特征
```

## 📝 代码示例

### 完整代码（最小示例）

```python
from pathlib import Path
from convert_geojson_for_floris import GeoJSONToFLORISConverter
from floris import FlorisModel
from floris.optimization.layout_optimization.layout_optimization_gridded import (
    LayoutOptimizationGridded,
)
import matplotlib.pyplot as plt

# 1. 转换坐标
converter = GeoJSONToFLORISConverter('data/changpin.geojson')
boundaries = converter.get_floris_boundaries(0, auto_crs=True)

# 2. 加载模型
fmodel = FlorisModel('inputs/gch.yaml')

# 3. 创建优化器
layout_opt = LayoutOptimizationGridded(
    fmodel, boundaries, min_dist_D=5.0
)

# 4. 优化和结果
layout_opt.optimize()
layout_opt.plot_layout_opt_results()
plt.show()
```

## ⚠️ 常见问题

**Q: 转换后的坐标单位是什么？**

A: 单位是 **米 (m)**。这是投影坐标系（UTM）的标准单位。

**Q: 脚本自动选择的 UTM 区号是否正确？**

A: 对于北京地区，自动选择的通常是 **UTM Zone 50N (EPSG:32650)**，这是正确的。

**Q: 如何修改投影坐标系？**

A: 修改转换器初始化：
```python
converter = GeoJSONToFLORISConverter(
    'data/changpin.geojson',
    target_crs="EPSG:2401"  # 改为高斯-克吕格投影
)
```

**Q: 优化时间很长，如何加快？**

A: 调整参数：
```python
layout_opt = LayoutOptimizationGridded(
    fmodel, boundaries,
    min_dist_D=5.0,
    rotation_step=10.0,      # 增大步长
    translation_step_D=2.0,  # 增大步长
)
```

**Q: 如何只显示优化结果不进行 AEP 计算？**

A: 注释掉 AEP 计算部分（会大幅加快）：
```python
# fmodel.set(layout_x=x_opt, layout_y=y_opt)
# fmodel.run()
# aep_total = fmodel.get_farm_AEP()
```

## 📚 相关文档

- [FLORIS 官方文档](https://floris.readthedocs.io/)
- [GeoJSON 规范](https://geojson.org/)
- [pyproj 坐标转换](https://pyproj4.github.io/pyproj/)
- [UTM 投影参考](https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system)

## ✅ 验证检查清单

运行脚本前，确保：

- [ ] FLORIS 已安装：`pip list | grep floris`
- [ ] 坐标转换库已安装：`pip list | grep pyproj`
- [ ] GeoJSON 文件存在：`ls wind/data/changpin.geojson`
- [ ] FLORIS 配置文件存在：`ls inputs/gch.yaml`
- [ ] 有足够的磁盘空间（约 100MB 用于结果）
- [ ] Python 版本 ≥ 3.8

## 📞 调试支持

遇到问题时，查看以下日志：

```bash
# 查看详细错误信息
python changpin_gridded_layout_optimization.py > optimization.log 2>&1

# 检查转换结果
python -c "from convert_geojson_for_floris import GeoJSONToFLORISConverter; c = GeoJSONToFLORISConverter('data/changpin.geojson'); print(c.list_features_info())"
```

---

**最后更新**: 2026-04-16
**作者**: FLORIS 优化工具团队
