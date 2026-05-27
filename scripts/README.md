# 行政区划 GeoJSON 数据处理工具

这个工具集允许您使用 QGIS 和 Python 从 GeoJSON 文件中读取行政区划数据，并获取相应的多边形范围，以及转换为 FLORIS 布局优化所需的投影坐标系。

## ⚠️ 重要：关于坐标系统

### QGIS/GeoJSON 提供的坐标 vs FLORIS 需要的坐标

| 特性 | GeoJSON (QGIS) | FLORIS boundaries |
|-----|---|---|
| **坐标系** | 经纬度 (WGS84, EPSG:4326) | 投影坐标系 (笛卡尔坐标) |
| **单位** | 度 (°) | 米 (m) |
| **范围示例** | 120.123°E, 30.456°N | 500000.12, 3380000.45 |
| **不能直接使用** | ❌ | ✓ |

**重要结论：**
- ✓ `boundaries` 中的数据是 **笛卡尔平面坐标（米为单位）**，NOT 经纬度
- ❌ QGIS 返回的 MultiPolygon 坐标 (经纬度) **不能直接用于 FLORIS**
- ⚙️ 需要进行坐标转换（经纬度 → 投影坐标系）

## 文件说明

### `read_geojson_with_qgis.py`
主要模块，包含 `AdministrativeDivisionReader` 类，提供以下功能：

- **加载 GeoJSON 文件** - 读取并解析 GeoJSON 格式的地理数据
- **列出行政区划** - 显示所有可用的行政区划名称
- **获取多边形范围** - 根据索引或名称获取特定行政区划的边界框
- **计算面积** - 使用 Shoelace 公式计算多边形面积
- ⚠️ **注意** - 返回的是经纬度坐标，不能直接用于 FLORIS

### `convert_geojson_for_floris.py` ⭐ **关键工具**
🔑 **核心转换工具** - 将 GeoJSON 坐标转换为 FLORIS 所需的投影坐标系

包含 `GeoJSONToFLORISConverter` 类，提供以下功能：

- **自动UTM区号检测** - 根据坐标自动选择合适的投影坐标系
- **经纬度转投影坐标** - 批量转换坐标（使用 pyproj）
- **支持 Polygon 和 MultiPolygon** - 处理复杂的几何体
- **导出为 FLORIS 格式** - 直接生成可用的 boundaries 列表
- ✅ **返回 FLORIS 可用格式** - List[Tuple[float, float]]（单位：米）

### `floris_integration_guide.py` ⭐ **完整教程**
📚 **学习指南** - 坐标系统转换和 FLORIS 集成的详细说明

包含 5 个教学示例：
1. 坐标系统理解
2. 单个多边形转换
3. 多部分多边形处理
4. 与 FLORIS 布局优化集成
5. 坐标转换前后对比

### `example_usage.py`
包含四个实际使用示例：
1. 基本使用方法
2. 获取特定行政区划的范围
3. 按名称查询行政区划
4. 导出边界数据为 JSON

## 安装依赖

### 核心依赖（必需）

```bash
pip install pyproj shapely geojson
```

- `pyproj` - **必需**，用于坐标系统转换（经纬度 ↔ 投影坐标）
- `shapely` - 处理几何体
- `geojson` - 读取 GeoJSON 文件

### 可选：PyQGIS（用于与 QGIS 直接交互）

**Ubuntu/Debian:**
```bash
sudo apt-get install qgis python3-qgis python3-pyqt5
```

**macOS (using Homebrew):**
```bash
brew install qgis
```

**Windows:**
从 [QGIS 官网](https://qgis.org/download/) 下载并安装

### 可选：用于 FLORIS 集成

```bash
pip install floris matplotlib numpy
```

## 获取数据

1. 访问 [天地图平台](https://cloudcenter.tianditu.gov.cn/administrativeDivision)
2. 下载感兴趣的行政区划 GeoJSON 文件
3. 将文件重命名为 `administrative_division.geojson`
4. 放在此目录中

## 使用方法

### 步骤 1: 从 GeoJSON 读取数据（经纬度）

```python
from read_geojson_with_qgis import AdministrativeDivisionReader

# 加载 GeoJSON 文件
reader = AdministrativeDivisionReader("administrative_division.geojson")

# 列出所有行政区划
divisions = reader.list_divisions()
for div in divisions:
    print(f"{div['index']}: {div['name']}")

# 获取第一个行政区划的多边形范围（经纬度坐标）
bounds = reader.get_polygon_bounds(0)
print(f"经度范围: [{bounds['min_lon']}, {bounds['max_lon']}]")
print(f"纬度范围: [{bounds['min_lat']}, {bounds['max_lat']}]")
```

**⚠️ 这时的坐标是经纬度，不能直接用于 FLORIS**

### 步骤 2: 转换为投影坐标（笛卡尔坐标，米）

```python
from convert_geojson_for_floris import GeoJSONToFLORISConverter

# 创建转换器（自动检测 UTM 区号）
converter = GeoJSONToFLORISConverter("administrative_division.geojson")

# 获取 FLORIS 可用的 boundaries（投影坐标，单位：米）
boundaries = converter.get_floris_boundaries(0, auto_crs=True)

print(f"FLORIS boundaries: {boundaries[:3]}...")  # 显示前 3 个点
```

**返回格式: [(x1, y1), (x2, y2), ...]，单位为米**

### 步骤 3: 用于 FLORIS 布局优化

```python
from floris import FlorisModel
from floris.optimization.layout_optimization.layout_optimization_gridded import (
    LayoutOptimizationGridded,
)

# 加载 FlorisModel
fmodel = FlorisModel('config.yaml')

# 使用转换后的 boundaries
layout_opt = LayoutOptimizationGridded(
    fmodel,
    boundaries,           # ✅ 投影坐标（米）
    min_dist_D=5.0       # 5 个风机直径的间距
)

# 运行优化
layout_opt.optimize()
layout_opt.plot_layout_opt_results()
```

### 按名称查询（经纬度）

```python
# 根据名称获取行政区划（仍为经纬度）
bounds = reader.get_polygon_bounds_by_name("北京市")
print(f"北京市的边界: {bounds}")
```

### 运行教程和示例

```bash
# 查看完整教程（包括图解和对比）
python floris_integration_guide.py

# 运行实际示例（需要 GeoJSON 文件）
python example_usage.py

# 测试坐标转换
python convert_geojson_for_floris.py
```

## 返回数据格式

### GeoJSON 读取结果（经纬度）

`read_geojson_with_qgis.get_polygon_bounds()` 返回包含以下信息的字典：

```python
{
    'min_lon': float,           # 最小经度
    'max_lon': float,           # 最大经度
    'min_lat': float,           # 最小纬度
    'max_lat': float,           # 最大纬度
    'center_lon': float,        # 中心经度
    'center_lat': float,        # 中心纬度
    'coordinates': [[lon, lat], ...],  # 多边形顶点坐标（经纬度）
    'properties': {             # GeoJSON 属性
        'name': str,
        ...
    }
}
```

### FLORIS boundaries（投影坐标）

`convert_geojson_for_floris.get_floris_boundaries()` **返回可直接用于 FLORIS 的格式**：

#### 单个多边形（最常用）
```python
boundaries = [(x1, y1), (x2, y2), (x3, y3), ..., (x1, y1)]
# 单位：米（m）
# 类型：List[Tuple[float, float]]
```

#### 多个独立区域（MultiPolygon）
```python
boundaries = [
    [(x1, y1), (x2, y2), ..., (x1, y1)],  # 区域 1
    [(x1, y1), (x2, y2), ..., (x1, y1)],  # 区域 2
]
# 单位：米（m）
# 类型：List[List[Tuple[float, float]]]
```

**⚠️ 关键区别：**
- 📍 GeoJSON: 经纬度，单位°（度）
- 📍 FLORIS: 投影坐标，单位m（米）
- 👉 **不能混淆使用！**


## 类方法参考

### `AdministrativeDivisionReader` - 读取 GeoJSON

#### `__init__(geojson_path: str)`
初始化读取器并加载 GeoJSON 文件

#### `list_divisions(name_field: str = 'name') -> List[Dict]`
列出所有行政区划
- 返回包含 index, name, properties 的列表

#### `get_polygon_bounds(division_index: int) -> Dict`
根据索引获取多边形范围（经纬度）

#### `get_polygon_bounds_by_name(division_name: str, name_field: str = 'name') -> Dict`
根据名称获取多边形范围（经纬度）

#### `calculate_area(coordinates: List[List[float]]) -> float`
计算多边形面积（使用 Shoelace 公式）

### `GeoJSONToFLORISConverter` - 坐标转换 ⭐

#### `__init__(geojson_path: str, target_crs: str = "EPSG:32650")`
初始化转换器
- `geojson_path`: GeoJSON 文件路径
- `target_crs`: 目标投影坐标系（默认 UTM Zone 50N）

#### `get_floris_boundaries(feature_index: int, combine_multipolygon: bool = False, auto_crs: bool = True)`
🔑 **核心方法** - 获取 FLORIS 可用的 boundaries

- `feature_index`: 特征索引
- `combine_multipolygon`: 是否合并多部分多边形
- `auto_crs`: 是否根据坐标自动选择 UTM 区号
- **返回**: List[Tuple[float, float]]（投影坐标，单位米）

#### `list_features_info() -> List[Dict]`
列出所有特征的信息，包括类型、属性、面积等

#### `convert_polygon_to_floris_format(feature_index: int, auto_crs: bool = True)`
手动转换单个特征的坐标

#### `get_utm_zone_from_coords(lon: float, lat: float) -> int`
根据经纬度计算 UTM 区号

## GeoJSON 格式说明

预期的 GeoJSON 格式：

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "行政区划名称",
        ...
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [lng, lat],
            [lng, lat],
            ...
          ]
        ]
      }
    }
  ]
}
```

## 常见问题

### 坐标系统相关

**Q: 📍 GeoJSON 中的坐标是什么格式？能直接用于 FLORIS 吗？**

A: 
- GeoJSON 使用经纬度坐标（WGS84, EPSG:4326）
- ❌ **不能**直接用于 FLORIS
- ✅ 需要使用 `GeoJSONToFLORISConverter` 转换为投影坐标系

示例：
```python
# ❌ 错误做法
lon, lat = 120.123, 30.456
fmodel = FlorisModel(...)
layout_opt = LayoutOptimizationGridded(fmodel, [(lon, lat)])  # 错误！

# ✅ 正确做法
converter = GeoJSONToFLORISConverter(geojson_file)
boundaries = converter.get_floris_boundaries(0)  # 返回投影坐标（米）
layout_opt = LayoutOptimizationGridded(fmodel, boundaries)  # 正确
```

**Q: 💡 什么是投影坐标系？为什么 FLORIS 需要它？**

A:
- 投影坐标系将地球表面映射到平面（笛卡尔坐标）
- 单位是米，便于计算距离和面积
- FLORIS 模型假设风电场在水平平面上，所以需要笛卡尔坐标
- 经纬度是曲面坐标，不能直接计算欧氏距离

**Q: 🌍 脚本如何选择投影坐标系？**

A:
- 默认使用 UTM（通用横轴墨卡托投影）
- 对于中国东部：通常使用 UTM Zone 50N (EPSG:32650)
- 脚本有 `auto_crs=True` 选项，根据第一个点的经纬度自动选择 UTM 区号
- 可以手动指定: `converter = GeoJSONToFLORISConverter(geojson_file, target_crs="EPSG:32649")`

**Q: 📊 转换后的坐标如何理解？**

A:
```
经纬度坐标 (120.123, 30.456) 
   ↓ 转换 (使用 pyproj)
投影坐标 (500012.45, 3380123.67)

解释：
- X = 500012.45 m  (东向距 UTM Zone 50 中线的距离)
- Y = 3380123.67 m (北向距赤道的距离)
```

### 功能相关

**Q: 如何处理多部分多边形（MultiPolygon）？**

A: 两种方式：
```python
# 方式 1: 保留分离（适合多个独立风电场）
boundaries = converter.convert_polygon_to_floris_format(
    feature_index, 
    auto_crs=True
)  # 返回 [[(x,y), ...], [(x,y), ...]]

# 方式 2: 合并为单个边界
boundaries_combined = converter.get_floris_boundaries(
    feature_index,
    combine_multipolygon=True,
    auto_crs=True
)  # 返回 [(x,y), (x,y), ...]
```

**Q: 计算的面积单位是什么？**

A: 
- GeoJSON 面积（Shoelace 公式）：平方度 （°²）
- 投影坐标面积：平方米（m²）
- 转换方法：需要考虑纬度，无简单公式，建议用 Shapely 库

**Q: 如何更换地区？**

A: 
1. 下载不同地区的 GeoJSON 文件
2. 脚本自动选择合适的 UTM 区号（`auto_crs=True`）
3. 或手动指定投影坐标系

### 集成相关

**Q: 转换后的 boundaries 如何用于 FLORIS 布局优化？**

A: 
```python
from floris import FlorisModel
from floris.optimization.layout_optimization.layout_optimization_gridded import (
    LayoutOptimizationGridded,
)
from convert_geojson_for_floris import GeoJSONToFLORISConverter

# 1. 转换坐标
converter = GeoJSONToFLORISConverter('administrative_division.geojson')
boundaries = converter.get_floris_boundaries(0, auto_crs=True)

# 2. 创建优化器
fmodel = FlorisModel('config.yaml')
layout_opt = LayoutOptimizationGridded(
    fmodel,
    boundaries,  # ✅ 投影坐标（米）
    min_dist_D=5.0  # 5 个风机直径
)

# 3. 运行优化
layout_opt.optimize()
```

**Q: 是否支持其他投影坐标系（如 Mercator）？**

A: 支持！修改 `target_crs` 参数：
```python
converter = GeoJSONToFLORISConverter(
    geojson_file,
    target_crs="EPSG:3395"  # 世界墨卡托投影
)
```

## 许可证

本工具供学习和研究使用。

## 参考资源

- [QGIS 文档](https://docs.qgis.org/)
- [GeoJSON 规范](https://geojson.org/)
- [天地图 API 文档](https://lbs.tianditu.gov.cn/api/js4.0/index.html)
- [pyproj 文档](https://pyproj4.github.io/pyproj/)
- [Shapely 文档](https://shapely.readthedocs.io/)
- [UTM 投影参考](https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system)

