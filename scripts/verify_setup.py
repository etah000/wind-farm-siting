#!/usr/bin/env python3
"""
验证脚本：检查所有依赖和配置是否正确
"""

import sys
from pathlib import Path

print("=" * 70)
print("FLORIS GeoJSON 优化工具 - 环境检查")
print("=" * 70)

# 检查 1: Python 版本
print("\n[1] Python 版本")
python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
print(f"    ✓ Python {python_version}")

# 检查 2: 必需库
print("\n[2] 必需库检查")

required_packages = {
    'floris': 'FLORIS 风电场模型库',
    'pyproj': '坐标系统转换库',
    'shapely': '几何体处理库',
    'geojson': 'GeoJSON 格式支持',
    'numpy': '数值计算库',
    'matplotlib': '绘图库',
}

all_ok = True
for package, description in required_packages.items():
    try:
        __import__(package)
        print(f"    ✓ {package:<15} - {description}")
    except ImportError:
        print(f"    ❌ {package:<15} - {description} [未安装]")
        all_ok = False

# 检查 3: 数据文件
print("\n[3] 数据文件检查")

data_files = {
    'changpin.geojson': '/wind/data/changpin.geojson',
    'fangshan.geojson': '/wind/data/fangshan.geojson',
    'beijing.geojson': '/wind/data/beijing.geojson',
}

base_path = Path(__file__).parent

for filename, rel_path in data_files.items():
    file_path = base_path / rel_path.lstrip('/')
    if file_path.exists():
        file_size = file_path.stat().st_size
        print(f"    ✓ {filename:<20} ({file_size} bytes)")
    else:
        print(f"    ❌ {filename:<20} [未找到]")
        all_ok = False

# 检查 4: 配置文件
print("\n[4] FLORIS 配置文件检查")

config_paths = [
    base_path / '..' / 'inputs' / 'gch.yaml',
    base_path.parent.parent / 'inputs' / 'gch.yaml',
    base_path.parent.parent / 'examples' / 'inputs' / 'gch.yaml',
]

config_found = False
for config_path in config_paths:
    if config_path.exists():
        print(f"    ✓ gch.yaml 找到: {config_path}")
        config_found = True
        break

if not config_found:
    print(f"    ❌ gch.yaml [未找到]")
    all_ok = False

# 检查 5: 工具脚本
print("\n[5] 工具脚本检查")

tool_scripts = {
    'convert_geojson_for_floris.py': 'test/convert_geojson_for_floris.py',
    'read_geojson_with_qgis.py': 'test/read_geojson_with_qgis.py',
    'example_usage.py': 'test/example_usage.py',
}

for script_name, rel_path in tool_scripts.items():
    script_path = base_path / rel_path
    if script_path.exists():
        print(f"    ✓ {script_name}")
    else:
        print(f"    ❌ {script_name} [未找到]")
        all_ok = False

# 检查 6: 主脚本
print("\n[6] 主优化脚本检查")

main_script = base_path / 'changpin_gridded_layout_optimization.py'
if main_script.exists():
    print(f"    ✓ changpin_gridded_layout_optimization.py")
else:
    print(f"    ❌ changpin_gridded_layout_optimization.py [未找到]")
    all_ok = False

# 总结
print("\n" + "=" * 70)
if all_ok:
    print("✅ 所有检查通过！可以运行优化脚本")
    print("\n快速开始:")
    print("  cd /home/frank/opensource/floris/wind")
    print("  python changpin_gridded_layout_optimization.py")
else:
    print("⚠️  检查到一些问题，请先解决后再运行")
    print("\n快速安装指南:")
    print("  pip install floris pyproj shapely geojson numpy matplotlib")

print("=" * 70)
