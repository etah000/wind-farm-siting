#!/usr/bin/env python3
"""
使用 read_geojson_with_qgis 和 convert_geojson_for_floris 模块的集成示例

演示如何：
1. 加载 GeoJSON 数据
2. 列出所有行政区划
3. 获取特定行政区划的多边形范围
4. 计算多边形的面积
5. 转换坐标为 FLORIS 格式
6. 使用 FLORIS gridded layout 进行优化
"""

import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from read_geojson_with_qgis import AdministrativeDivisionReader
from convert_geojson_for_floris import GeoJSONToFLORISConverter

try:
    from floris import FlorisModel
    from floris.optimization.layout_optimization.layout_optimization_gridded import (
        LayoutOptimizationGridded,
    )
    FLORIS_AVAILABLE = True
except ImportError:
    FLORIS_AVAILABLE = False
    print("警告: FLORIS 未安装。跳过布局优化示例。")


def example_1_basic_usage():
    """示例 1: 基本使用方法"""
    print("=" * 60)
    print("示例 1: 基本使用方法")
    print("=" * 60)
    
    try:
        geojson_file = Path(__file__).parent / "administrative_division.geojson"
        reader = AdministrativeDivisionReader(str(geojson_file))
        
        # 列出所有行政区划
        divisions = reader.list_divisions()
        print(f"\n共有 {len(divisions)} 个行政区划\n")
        
    except FileNotFoundError as e:
        print(f"文件不存在: {e}")
        print("\n请先下载 GeoJSON 数据并保存为 administrative_division.geojson")


def example_2_get_specific_division():
    """示例 2: 获取特定行政区划的多边形范围"""
    print("\n" + "=" * 60)
    print("示例 2: 获取特定行政区划的多边形范围")
    print("=" * 60)
    
    try:
        geojson_file = Path(__file__).parent / "administrative_division.geojson"
        reader = AdministrativeDivisionReader(str(geojson_file))
        
        # 按索引获取第一个行政区划
        bounds = reader.get_polygon_bounds(0)
        
        print(f"\n第 1 个行政区划:")
        print(f"  名称: {bounds['properties']}")
        print(f"  经度范围: [{bounds['min_lon']:.6f}, {bounds['max_lon']:.6f}]")
        print(f"  纬度范围: [{bounds['min_lat']:.6f}, {bounds['max_lat']:.6f}]")
        print(f"  中心坐标: ({bounds['center_lon']:.6f}, {bounds['center_lat']:.6f})")
        print(f"  顶点数: {len(bounds['coordinates'])}")
        
    except Exception as e:
        print(f"错误: {e}")


def example_3_get_by_name():
    """示例 3: 按名称获取行政区划"""
    print("\n" + "=" * 60)
    print("示例 3: 按名称获取行政区划")
    print("=" * 60)
    
    try:
        geojson_file = Path(__file__).parent / "administrative_division.geojson"
        reader = AdministrativeDivisionReader(str(geojson_file))
        
        # 列出所有行政区划名称
        divisions = reader.list_divisions()
        if divisions:
            # 尝试按第一个行政区划的名称查询
            division_name = divisions[0]['name']
            print(f"\n查询行政区划: {division_name}")
            
            bounds = reader.get_polygon_bounds_by_name(division_name)
            area = reader.calculate_area(bounds['coordinates'])
            
            print(f"  经度范围: [{bounds['min_lon']:.6f}, {bounds['max_lon']:.6f}]")
            print(f"  纬度范围: [{bounds['min_lat']:.6f}, {bounds['max_lat']:.6f}]")
            print(f"  面积: {area:.8f} 平方度")
    
    except Exception as e:
        print(f"错误: {e}")


def example_4_export_bounds():
    """示例 4: 导出多边形范围为 JSON"""
    print("\n" + "=" * 60)
    print("示例 4: 导出多边形范围为 JSON")
    print("=" * 60)
    
    try:
        geojson_file = Path(__file__).parent / "administrative_division.geojson"
        reader = AdministrativeDivisionReader(str(geojson_file))
        
        # 获取第一个行政区划并导出
        bounds = reader.get_polygon_bounds(0)
        
        # 创建导出数据
        export_data = {
            'division': bounds['properties'],
            'bounds': {
                'min_lon': bounds['min_lon'],
                'max_lon': bounds['max_lon'],
                'min_lat': bounds['min_lat'],
                'max_lat': bounds['max_lat'],
                'center': {
                    'longitude': bounds['center_lon'],
                    'latitude': bounds['center_lat']
                }
            },
            'coordinates_count': len(bounds['coordinates'])
        }
        
        output_file = Path(__file__).parent / "exported_bounds.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 已导出到: {output_file}")
        print("\n导出内容:")
        print(json.dumps(export_data, indent=2, ensure_ascii=False))
    
    except Exception as e:
        print(f"错误: {e}")


def example_5_floris_gridded_layout_optimization():
    """示例 5: 使用 FLORIS gridded layout 进行风电场优化"""
    print("\n" + "=" * 60)
    print("示例 5: FLORIS Gridded Layout 优化")
    print("=" * 60)
    
    if not FLORIS_AVAILABLE:
        print("❌ FLORIS 未安装，无法运行此示例")
        return
    
    try:
        # 1. 加载 GeoJSON 数据（使用 changpin.geojson）
        geojson_file = Path(__file__).parent.parent / "data" / "changpin.geojson"
        
        if not geojson_file.exists():
            print(f"❌ 文件不存在: {geojson_file}")
            return
        
        print(f"\n📍 加载 GeoJSON 数据: {geojson_file.name}")
        
        # 2. 转换坐标为投影坐标系
        print("\n🔄 转换坐标系统（经纬度 → 投影坐标）...")
        converter = GeoJSONToFLORISConverter(str(geojson_file))
        
        # 列出特征信息
        features_info = converter.list_features_info()
        print(f"   找到 {len(features_info)} 个特征")
        
        if not features_info:
            print("❌ 没有找到特征")
            return
        
        # 3. 获取边界坐标（自动选择 UTM 区号）
        feature_idx = 0
        print(f"\n📐 获取第 {feature_idx + 1} 个特征的边界...")
        boundaries = converter.get_floris_boundaries(feature_idx, auto_crs=True)
        
        print(f"   ✓ 成功获取 {len(boundaries)} 个顶点")
        
        # 显示边界信息
        xs = [coord[0] for coord in boundaries]
        ys = [coord[1] for coord in boundaries]
        
        print(f"\n   边界范围:")
        print(f"     X: [{min(xs):.2f}, {max(xs):.2f}] m")
        print(f"     Y: [{min(ys):.2f}, {max(ys):.2f}] m")
        print(f"     宽度: {max(xs) - min(xs):.2f} m")
        print(f"     高度: {max(ys) - min(ys):.2f} m")
        
        # 4. 加载 FLORIS 模型
        print(f"\n🔧 加载 FLORIS 模型...")
        # 寻找配置文件
        floris_config = Path(__file__).parent.parent.parent / "inputs" / "gch.yaml"
        if not floris_config.exists():
            # 尝试其他常见位置
            floris_config = Path(__file__).parent.parent.parent / "examples" / "inputs" / "gch.yaml"
        
        if not floris_config.exists():
            print(f"❌ 找不到 FLORIS 配置文件")
            return
        
        fmodel = FlorisModel(str(floris_config))
        print(f"   ✓ 模型加载成功")
        print(f"     风机类型: {fmodel.core.farm.turbine_type}")
        print(f"     风机数量: {len(fmodel.layout_x)}")
        
        # 5. 创建 Gridded Layout 优化器
        print(f"\n⚙️  设置 Gridded Layout 优化...")
        layout_opt = LayoutOptimizationGridded(
            fmodel,
            boundaries,
            min_dist_D=5.0,  # 5 倍风机直径的间距
            min_dist=None,
            rotation_step=5.0,
            translation_step_D=1.0,
        )
        print(f"   ✓ 优化器配置完成")
        
        # 6. 运行优化
        print(f"\n🚀 运行 Gridded Layout 优化...")
        layout_opt.optimize()
        print(f"   ✓ 优化完成")
        
        # 7. 获取优化结果
        x_opt = layout_opt.x
        y_opt = layout_opt.y
        
        print(f"\n📊 优化结果:")
        print(f"   风机数量: {len(x_opt)}")
        print(f"   风机位置范围:")
        print(f"     X: [{min(x_opt):.2f}, {max(x_opt):.2f}] m")
        print(f"     Y: [{min(y_opt):.2f}, {max(y_opt):.2f}] m")
        
        # 8. 计算 AEP（年发电量）
        print(f"\n⚡ 计算发电量...")
        fmodel.set(layout_x=x_opt, layout_y=y_opt)
        fmodel.run()
        aep = fmodel.get_farm_AEP()
        
        print(f"   AEP: {aep:.2e} kWh/year")
        print(f"   平均每机 AEP: {aep/len(x_opt):.2e} kWh/year")
        
        # 9. 导出结果
        results = {
            'region': features_info[feature_idx]['properties'],
            'optimization': {
                'turbine_count': len(x_opt),
                'spacing_D': 5.0,
                'aep_total': float(aep),
                'aep_per_turbine': float(aep / len(x_opt)),
            },
            'boundary': {
                'type': 'projected_coordinates_utm',
                'vertices': len(boundaries),
                'x_range': [float(min(xs)), float(max(xs))],
                'y_range': [float(min(ys)), float(max(ys))],
            },
            'turbine_positions': [
                {'x': float(x), 'y': float(y)} 
                for x, y in zip(x_opt, y_opt)
            ]
        }
        
        # 保存结果
        output_file = Path(__file__).parent / "floris_optimization_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 结果已导出: {output_file}")
        
        # 10. 可视化结果
        print(f"\n📈 绘制优化结果...")
        ax = layout_opt.plot_layout_opt_results()
        
        # 保存图表
        plot_file = Path(__file__).parent / "floris_layout_optimization_plot.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"   ✓ 图表已保存: {plot_file}")
        
        plt.show()
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()




if __name__ == "__main__":
    example_1_basic_usage()
    example_2_get_specific_division()
    example_3_get_by_name()
    example_4_export_bounds()
    
    # 新增：FLORIS 布局优化示例
    if FLORIS_AVAILABLE:
        example_5_floris_gridded_layout_optimization()
    else:
        print("\n" + "=" * 60)
        print("提示: 要运行 FLORIS 集成示例，请安装 FLORIS 库")
        print("=" * 60)
    
    print("\n" + "=" * 60)
    print("所有示例执行完毕")
    print("=" * 60)
