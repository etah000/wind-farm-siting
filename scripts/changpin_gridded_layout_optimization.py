#!/usr/bin/env python3
"""
风电场布局优化示例：使用 Changpin（昌平区）的 GeoJSON 边界数据

简化版本 - 仅获取风机位置和个数

该脚本演示：
1. 从 GeoJSON 文件加载行政区划边界
2. 将经纬度坐标转换为投影坐标（UTM）
3. 使用 FLORIS 的 Gridded Layout 优化算法获取初始风机位置
4. 导出风机位置信息

后续可使用这些风机位置进行进一步的优化或发电量计算。
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import time

try:
    from floris import FlorisModel
    from floris.optimization.layout_optimization.layout_optimization_gridded import (
        LayoutOptimizationGridded,
    )
except ImportError:
    print("❌ 错误: FLORIS 未安装")
    exit(1)

from boundary_trimmer import get_allowed_area, plot_shapely_geometry
from shapely.affinity import translate as shapely_translate

if __name__ == '__main__':
    print("=" * 80)
    print("FLORIS Gridded Layout - 风机位置初始化")
    print("=" * 80)

    # =========================================================================
    # 步骤 1: 加载 GeoJSON 数据
    # =========================================================================
    print("\n[步骤 1] 加载 GeoJSON 数据")
    print("-" * 80)

    geojson_file = Path(__file__).parent.parent / "data" / "fangshan.geojson"
    if not geojson_file.exists():
        print(f"❌ 文件不存在: {geojson_file}")
        exit(1)

    print(f"📍 加载文件: {geojson_file}")

    osm_pbf_file = Path(__file__).parent.parent / "data" / "beijing-260416.osm.pbf"
    if not osm_pbf_file.exists():
        print(f"❌ 文件不存在: {osm_pbf_file}")
        exit(1)

    print(f"📍 读取 OSM 文件: {osm_pbf_file}")
    # Use buffered exclusions (human=1000m, uninhabited=500m)
    boundary_utm, exclusions_utm, allowed_area, allowed_boundaries, target_crs = get_allowed_area(
        geojson_file,
        osm_pbf_file,
        buffer_human_m=1000.0,
        buffer_unhuman_m=500.0,
    )

    print(f"✓ 允许安装区域已计算，类型: {allowed_area.geom_type}")
    print(f"  目标 CRS: {target_crs}")
    print(f"  允许区域多边形数量: {len(allowed_boundaries)}")

    # Use the original (initial) changpin boundary as the maximum plotting bounds
    minx, miny, maxx, maxy = boundary_utm.bounds
    width = maxx - minx
    height = maxy - miny
    print(f"\n📊 允许安装区域范围 (投影坐标系):")
    print(f"  X: [{minx:.2f}, {maxx:.2f}] m")
    print(f"  Y: [{miny:.2f}, {maxy:.2f}] m")
    print(f"  宽度: {width:.2f} m")
    print(f"  高度: {height:.2f} m")
    print(f"  总面积: {allowed_area.area:.2f} m²")
    print(f"  排除面积: {exclusions_utm.area:.2f} m²")

    # =========================================================================
    # 步骤 4: 加载 FLORIS 模型
    # =========================================================================
    print("\n[步骤 4] 加载 FLORIS 模型")
    print("-" * 80)

    possible_paths = [
        Path(__file__).parent / ".." / "examples" / "inputs" / "gch.yaml",
        Path(__file__).parent.parent / "examples" / "inputs" / "gch.yaml",
        Path(__file__).parent.parent.parent / "examples" / "inputs" / "gch.yaml",
    ]

    floris_config = None
    for path in possible_paths:
        if path.exists():
            floris_config = path
            break

    if floris_config is None:
        print(f"❌ 找不到 FLORIS 配置文件，已搜索路径：")
        for path in possible_paths:
            print(f"   - {path}")
        exit(1)

    fmodel = FlorisModel(str(floris_config))
    rotor_diameter = fmodel.core.farm.rotor_diameters.flat[0]

    # Optional override: use a 10 kW turbine (approx small rotor diameter)
    # If you want to change the turbine size, set `override_turbine=True`
    override_turbine = True
    turbine_override_name = '10kW_custom'
    # Approximate rotor diameter for a small 10 kW turbine (meters)
    rotor_diameter_override = 10.0

    rotor_diameter_used = rotor_diameter_override if override_turbine else rotor_diameter

    print(f"✓ 模型加载成功")
    print(f"  原始风机类型: {fmodel.core.farm.turbine_type}")
    print(f"  原始风机直径: {rotor_diameter:.2f} m")
    if override_turbine:
        print(f"  使用覆盖风机: {turbine_override_name} (直径 {rotor_diameter_used:.2f} m)")

    # =========================================================================
    # 步骤 5: 运行 Gridded Layout 优化
    # =========================================================================
    print("\n[步骤 5] 运行 Gridded Layout 优化")
    print("-" * 80)

    min_dist_D = 5.0
    # Use rotor_diameter_used (overridden for 10kW if specified) to compute spacing
    min_dist = min_dist_D * rotor_diameter_used

    print(f"⚙️  优化参数:")
    print(f"  最小间距: {min_dist_D}D = {min_dist:.2f} m")
    print(f"  网格类型: 方形")

    layout_opt = LayoutOptimizationGridded(
        fmodel,
        allowed_boundaries,
        min_dist_D=None,
        min_dist=min_dist,
        rotation_step=5.0,
        translation_step_D=1.0,
    )

    # 使用 Shapely 允许区域，确保禁用区和孔洞被正确处理
    layout_opt._boundary_polygon = allowed_area
    layout_opt._boundary_line = allowed_area.boundary
    layout_opt.xmin, layout_opt.ymin, layout_opt.xmax, layout_opt.ymax = allowed_area.bounds

    print("\n 执行优化...")
    start_time = time.time()
    layout_opt.optimize()
    end_time = time.time()
    elapsed = end_time - start_time
    print("✓ 优化完成!")
    print(f"⏱️ 优化耗时: {elapsed:.2f} 秒")

    # =========================================================================
    # 步骤 6: 获取结果
    # =========================================================================
    print("\n[步骤 6] 获取优化结果")
    print("-" * 80)

    x_opt = layout_opt.x_opt
    y_opt = layout_opt.y_opt

    # Center shifts: use initial changpin boundary centroid (midpoint of bounds)
    center_x = (minx + maxx) / 2.0
    center_y = (miny + maxy) / 2.0
    x_opt_shifted = [x - center_x for x in x_opt]
    y_opt_shifted = [y - center_y for y in y_opt]
    # For plotting allowed polygon vertices relative positions (if needed)
    xs = [coord[0] for boundary in allowed_boundaries for coord in boundary]
    ys = [coord[1] for boundary in allowed_boundaries for coord in boundary]
    xs_shifted = [x - center_x for x in xs]
    ys_shifted = [y - center_y for y in ys]

    fig, ax = plt.subplots(figsize=(10, 8))
    # Translate geometries so they align with shifted turbine coordinates
    boundary_shifted = shapely_translate(boundary_utm, xoff=-center_x, yoff=-center_y)
    allowed_area_shifted = shapely_translate(allowed_area, xoff=-center_x, yoff=-center_y)
    plot_shapely_geometry(ax, boundary_shifted, edge_color='blue', alpha=1.0, linewidth=2)
    plot_shapely_geometry(ax, allowed_area_shifted, edge_color='gray', alpha=0.8, linewidth=2)
    turbine_scatter = ax.scatter(x_opt_shifted, y_opt_shifted, c='red', s=50, marker='o', label='Turbines')
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title('Wind Farm Layout Optimization - Allowed Installation Area')
    ax.legend(handles=[
        Line2D([0], [0], color='blue', linewidth=2, label='Original boundary'),
        Line2D([0], [0], color='gray', linewidth=2, label='Trimmed boundary'),
        turbine_scatter,
    ], loc='best')
    ax.axis('equal')
    ax.grid(True, alpha=0.3)
    # Set axes limits to the initial changpin boundary (with small padding)
    pad = max(width, height) * 0.02
    ax.set_xlim(minx - center_x - pad, maxx - center_x + pad)
    ax.set_ylim(miny - center_y - pad, maxy - center_y + pad)
    plt.tight_layout()
    fig.savefig(Path(__file__).parent / 'Figure_1.png', dpi=200)
    plt.show()

    print(f"✓ 图像已保存到: {Path(__file__).parent / 'Figure_1.png'}")
    print(f"📊 结果:")
    print(f"  风机数量: {len(x_opt)}")
    if x_opt.size if hasattr(x_opt, 'size') else len(x_opt):
        print(f"  风机位置范围:")
        print(f"    X: [{min(x_opt):.2f}, {max(x_opt):.2f}] m")
        print(f"    Y: [{min(y_opt):.2f}, {max(y_opt):.2f}] m")

    # =========================================================================
    # 步骤 7: 导出结果
    # =========================================================================
    print("\n[步骤 7] 导出结果")
    print("-" * 80)

    allowed_xs = [coord[0] for boundary in allowed_boundaries for coord in boundary]
    allowed_ys = [coord[1] for boundary in allowed_boundaries for coord in boundary]

    results = {
        'metadata': {
            'region': 'Changpin District (昌平区)',
            'geojson_file': 'changpin.geojson',
            'osm_pbf_file': 'beijing-260416.osm.pbf',
            'method': 'Gridded Layout (Initial Positions with OSM Exclusions)',
            'target_crs': target_crs,
        },
        'parameters': {
            'spacing_D': min_dist_D,
            'spacing_m': min_dist,
            'allowed_polygons': len(allowed_boundaries),
            'excluded_area_m2': float(exclusions_utm.area),
            'allowed_area_m2': float(allowed_area.area),
        },
        'results': {
            'turbine_count': len(x_opt),
        },
        'boundary': {
            'crs': target_crs,
            'x_range_m': [float(min(allowed_xs)), float(max(allowed_xs))],
            'y_range_m': [float(min(allowed_ys)), float(max(allowed_ys))],
        },
        'turbine_locations': [
            {'id': i, 'x_m': float(x_opt[i]), 'y_m': float(y_opt[i])}
            for i in range(len(x_opt))
        ]
    }

    output_file = Path(__file__).parent / "changpin_optimization_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✓ 结果已导出到: {output_file}")

    print("\n" + "=" * 80)
    print("✅ 优化完成!")
    print("=" * 80)
    print(f"\n📋 总结:")
    print(f"  📍 地区: 昌平区")
    print(f"  🌪️  风机数量: {len(x_opt)}")
    print(f"  📁 结果文件: {output_file}")
    print(f"\n💡 后续步骤:")
    print(f"  • 使用这些风机位置进行进一步优化")
    print(f"  • 计算发电量（AEP）")
    print(f"  • 应用其他优化算法")
    print("=" * 80)
