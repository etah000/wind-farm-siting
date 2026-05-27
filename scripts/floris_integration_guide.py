#!/usr/bin/env python3
"""
完整示例：使用 QGIS GeoJSON 数据进行 FLORIS 布局优化

流程：
1. 从 QGIS/天地图获取 GeoJSON 数据（经纬度坐标）
2. 转换为投影坐标系（笛卡尔坐标，单位米）
3. 用于 FLORIS 布局优化
"""

from pathlib import Path
from convert_geojson_for_floris import GeoJSONToFLORISConverter


def example_1_understanding_coordinate_systems():
    """示例 1: 理解坐标系统"""
    print("=" * 80)
    print("示例 1: 理解 FLORIS 所需的坐标系统")
    print("=" * 80)
    
    print("""
📍 QGIS/GeoJSON 提供的坐标：
   - 类型: 经纬度 (WGS84, EPSG:4326)
   - 范围: 经度 [-180°, 180°], 纬度 [-90°, 90°]
   - 例子: (120.1234, 30.5678)  <- 这是上海附近的坐标
   - 不能直接用于 FLORIS！

🤖 FLORIS 需要的坐标：
   - 类型: 投影坐标系（笛卡尔坐标）
   - 单位: 米 (m)
   - 例子: (500000.12, 3380000.45)  <- UTM 投影坐标
   - 这样距离计算才准确

⚙️ 坐标转换过程：
   经纬度 (WGS84) 
       ↓ 
   pyproj 库进行转换
       ↓
   投影坐标 (UTM 或其他投影系)
       ↓
   用于 FLORIS 布局优化

🌍 中国常用坐标系：
   - UTM Zone 49N (EPSG:32649) - 西部地区 (74°E - 84°E)
   - UTM Zone 50N (EPSG:32650) - 东部地区 (84°E - 94°E)
   - 高斯-克吕格投影 (EPSG:2381-2426)
   
   提示: 自动检测功能会根据第一个坐标点自动选择合适的 UTM 区号
    """)


def example_2_convert_single_polygon():
    """示例 2: 转换单个多边形区域"""
    print("\n" + "=" * 80)
    print("示例 2: 转换单个多边形区域")
    print("=" * 80)
    
    geojson_file = Path(__file__).parent / "administrative_division.geojson"
    
    if not geojson_file.exists():
        print(f"❌ 文件不存在: {geojson_file}")
        return
    
    try:
        # 创建转换器
        converter = GeoJSONToFLORISConverter(str(geojson_file))
        
        # 获取第一个特征的 FLORIS boundaries
        boundaries = converter.get_floris_boundaries(0, auto_crs=True)
        
        print(f"\n✓ 获取到 FLORIS boundaries：")
        print(f"  顶点数: {len(boundaries)}")
        print(f"  格式: List[Tuple[float, float]]")
        
        # 显示前 3 个顶点
        print(f"\n  前 3 个顶点 (单位: 米):")
        for i, (x, y) in enumerate(boundaries[:3]):
            print(f"    {i+1}. x={x:.2f}, y={y:.2f}")
        
        # 计算边界框
        xs = [coord[0] for coord in boundaries]
        ys = [coord[1] for coord in boundaries]
        
        print(f"\n  边界框:")
        print(f"    X 范围: [{min(xs):.2f}, {max(xs):.2f}]")
        print(f"    Y 范围: [{min(ys):.2f}, {max(ys):.2f}]")
        print(f"    宽度: {max(xs) - min(xs):.2f} m")
        print(f"    高度: {max(ys) - min(ys):.2f} m")
        
    except Exception as e:
        print(f"❌ 错误: {e}")


def example_3_convert_multipolygon():
    """示例 3: 处理多部分多边形"""
    print("\n" + "=" * 80)
    print("示例 3: 处理多部分多边形 (MultiPolygon)")
    print("=" * 80)
    
    geojson_file = Path(__file__).parent / "administrative_division.geojson"
    
    if not geojson_file.exists():
        print(f"❌ 文件不存在: {geojson_file}")
        return
    
    try:
        converter = GeoJSONToFLORISConverter(str(geojson_file))
        
        # 获取特征信息
        features_info = converter.list_features_info()
        
        # 查找 MultiPolygon
        multipolygons = [f for f in features_info if f['type'] == 'MultiPolygon']
        
        if multipolygons:
            idx = multipolygons[0]['index']
            print(f"\n找到 MultiPolygon 特征 (索引: {idx})")
            
            # 不合并，获取原始格式
            boundaries = converter.convert_polygon_to_floris_format(idx, auto_crs=True)
            
            print(f"  包含 {len(boundaries)} 个独立多边形:")
            for i, poly in enumerate(boundaries):
                print(f"    多边形 {i+1}: {len(poly)} 个顶点")
            
            print(f"\n  FLORIS 使用方法（分离的多边形区域）:")
            print(f"    boundaries = [")
            for i, poly in enumerate(boundaries):
                print(f"        { # 多边形 {i+1}")
                for j, (x, y) in enumerate(poly[:2]):
                    marker = "..." if j == 1 and len(poly) > 2 else ""
                    print(f"            ({x:.2f}, {y:.2f}), {marker}")
                print(f"        },")
            print(f"    ]")
        else:
            print("  未找到 MultiPolygon 特征")
        
    except Exception as e:
        print(f"❌ 错误: {e}")


def example_4_integration_with_floris():
    """示例 4: 与 FLORIS 布局优化集成"""
    print("\n" + "=" * 80)
    print("示例 4: 与 FLORIS 布局优化集成")
    print("=" * 80)
    
    print("""
使用转换后的 boundaries 进行 FLORIS 布局优化的代码示例：

```python
from floris import FlorisModel
from floris.optimization.layout_optimization.layout_optimization_gridded import (
    LayoutOptimizationGridded,
)
from convert_geojson_for_floris import GeoJSONToFLORISConverter

# 1. 加载 FlorisModel
fmodel = FlorisModel('path/to/config.yaml')

# 2. 转换 GeoJSON 为 FLORIS boundaries
converter = GeoJSONToFLORISConverter('administrative_division.geojson')
boundaries = converter.get_floris_boundaries(0, auto_crs=True)

# 3. 设置布局优化
layout_opt = LayoutOptimizationGridded(
    fmodel,
    boundaries,
    min_dist_D=5.0  # 5 个风机直径的间距
)

# 4. 运行优化
layout_opt.optimize()

# 5. 可视化结果
layout_opt.plot_layout_opt_results()

import matplotlib.pyplot as plt
plt.show()
```

⚠️ 重要注意事项：
- 确保 boundaries 是投影坐标（米），不是经纬度！
- 取决于该区域的坐标范围，可能需要调整 UTM 区号
- FLORIS 假设是水平面坐标，不考虑地形高差
- 可视化时 X/Y 轴的单位是米 (m)
    """)


def example_5_comparison_coordinates():
    """示例 5: 坐标转换前后对比"""
    print("\n" + "=" * 80)
    print("示例 5: 坐标转换前后对比")
    print("=" * 80)
    
    print("""
示例坐标数据（中国东部）：

原始数据（经纬度）：
  纬度: 30.5°N
  经度: 120.1°E
  →  (120.1, 30.5)  [GeoJSON 格式]

转换后（UTM Zone 50N）：
  E: 500012.45 m (东向)
  N: 3380123.67 m (北向)
  →  (500012.45, 3380123.67)  [FLORIS 集成坐标]

距离换算示例：
  经纬度 1° 在地表距离约 111 km
  
  两个纬度点的距离：
    从 30.5°N 到 30.6°N 的距离 ≈ 111 km
    从 y=3380123.67 到 y=3391345.00 的距离 ≈ 11.2 km (差异由投影引起)

  两个经度点的距离：
    从 120.0°E 到 120.1°E 的距离 ≈ 111*cos(30.5°) ≈ 95.7 km
    从 x=489234.56 到 x=500456.78 的距离 ≈ 11.2 km (单位米)

结论：
  📌 在笛卡尔坐标系中，距离计算更直接准确
  📌 FLORIS 风电场模型假设水平面上的规则布局
  📌 地形影响需要单独处理
    """)


if __name__ == "__main__":
    example_1_understanding_coordinate_systems()
    
    try:
        example_2_convert_single_polygon()
    except Exception as e:
        print(f"跳过示例 2: {e}")
    
    try:
        example_3_convert_multipolygon()
    except Exception as e:
        print(f"跳过示例 3: {e}")
    
    example_4_integration_with_floris()
    example_5_comparison_coordinates()
    
    print("\n" + "=" * 80)
    print("所有示例完成！")
    print("=" * 80)
