#!/usr/bin/env python3
"""
使用 QGIS 从 GeoJSON 读取数据，获取行政区划的多边形范围

该脚本使用 PyQGIS 库来处理地理数据，支持：
- 读取 GeoJSON 文件
- 获取特定行政区划的多边形范围
- 提取边界坐标和面积等信息
"""

import os
import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional

try:
    from qgis.core import (
        QgsApplication,
        QgsVectorLayer,
        QgsGeometry,
        QgsRectangle,
        QgsFeature,
    )
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False
    print("警告: PyQGIS 未安装。将使用备用的 geojson 库处理数据。")


class AdministrativeDivisionReader:
    """读取和处理行政区划GeoJSON数据的类"""
    
    def __init__(self, geojson_path: str):
        """
        初始化读取器
        
        Args:
            geojson_path: GeoJSON 文件路径
        """
        self.geojson_path = Path(geojson_path)
        self.data = None
        self.features = []
        
        if not self.geojson_path.exists():
            raise FileNotFoundError(f"GeoJSON 文件不存在: {geojson_path}")
        
        self._load_geojson()
    
    def _load_geojson(self):
        """加载 GeoJSON 文件"""
        with open(self.geojson_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        if self.data.get('type') == 'FeatureCollection':
            self.features = self.data.get('features', [])
        else:
            raise ValueError("不支持的 GeoJSON 格式，期望 FeatureCollection")
        
        print(f"✓ 已加载 {len(self.features)} 个特征")
    
    def list_divisions(self, name_field: str = 'name') -> List[Dict]:
        """
        列出所有行政区划
        
        Args:
            name_field: 包含名称的字段名
            
        Returns:
            行政区划信息列表
        """
        divisions = []
        for idx, feature in enumerate(self.features):
            props = feature.get('properties', {})
            division_name = props.get(name_field, f"Feature_{idx}")
            divisions.append({
                'index': idx,
                'name': division_name,
                'properties': props
            })
        return divisions
    
    def get_polygon_bounds(self, division_index: int) -> Dict:
        """
        获取指定行政区划的多边形范围
        
        Args:
            division_index: 行政区划的索引
            
        Returns:
            包含多边形范围信息的字典
        """
        if division_index >= len(self.features):
            raise IndexError(f"索引超出范围: {division_index}")
        
        feature = self.features[division_index]
        geometry = feature.get('geometry', {})
        
        if geometry.get('type') != 'Polygon':
            raise ValueError(f"期望 Polygon 类型，获取: {geometry.get('type')}")
        
        coordinates = geometry.get('coordinates', [[]])[0]  # 获取外环坐标
        
        if not coordinates:
            raise ValueError("多边形没有坐标数据")
        
        # 计算边界框 (Bounding Box)
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]
        
        bounds = {
            'min_lon': min(lons),
            'max_lon': max(lons),
            'min_lat': min(lats),
            'max_lat': max(lats),
            'center_lon': (min(lons) + max(lons)) / 2,
            'center_lat': (min(lats) + max(lats)) / 2,
            'coordinates': coordinates,
            'properties': feature.get('properties', {})
        }
        
        return bounds
    
    def get_polygon_bounds_by_name(self, division_name: str, 
                                   name_field: str = 'name') -> Dict:
        """
        根据名称获取行政区划的多边形范围
        
        Args:
            division_name: 行政区划名称
            name_field: 包含名称的字段名
            
        Returns:
            包含多边形范围信息的字典
        """
        for idx, feature in enumerate(self.features):
            if feature.get('properties', {}).get(name_field) == division_name:
                return self.get_polygon_bounds(idx)
        
        raise ValueError(f"未找到行政区划: {division_name}")
    
    def calculate_area(self, coordinates: List[List[float]]) -> float:
        """
        使用 Shoelace 公式计算多边形面积（近似）
        
        Args:
            coordinates: 多边形坐标点列表
            
        Returns:
            面积（平方度）
        """
        if len(coordinates) < 3:
            return 0.0
        
        area = 0.0
        for i in range(len(coordinates) - 1):
            x1, y1 = coordinates[i]
            x2, y2 = coordinates[i + 1]
            area += (x1 * y2 - x2 * y1)
        
        return abs(area) / 2.0


def main():
    """主函数 - 演示如何使用"""
    
    # 示例：指定 GeoJSON 文件路径
    # 您可以从 https://cloudcenter.tianditu.gov.cn/administrativeDivision 获取数据
    
    geojson_file = Path(__file__).parent / "administrative_division.geojson"
    
    if not geojson_file.exists():
        print(f"示例 GeoJSON 文件不存在: {geojson_file}")
        print("\n使用说明:")
        print("1. 从天地图下载 GeoJSON 数据")
        print("2. 将文件保存为 administrative_division.geojson")
        print("3. 运行此脚本")
        return
    
    try:
        # 创建读取器实例
        reader = AdministrativeDivisionReader(str(geojson_file))
        
        # 列出所有行政区划
        divisions = reader.list_divisions()
        print("\n已有行政区划:")
        for div in divisions:
            print(f"  [{div['index']}] {div['name']}")
        
        # 获取第一个行政区划的多边形范围
        if divisions:
            bounds = reader.get_polygon_bounds(0)
            area = reader.calculate_area(bounds['coordinates'])
            
            print(f"\n第一个行政区划的多边形范围:")
            print(f"  名称: {bounds['properties']}")
            print(f"  经度范围: [{bounds['min_lon']:.4f}, {bounds['max_lon']:.4f}]")
            print(f"  纬度范围: [{bounds['min_lat']:.4f}, {bounds['max_lat']:.4f}]")
            print(f"  中心: ({bounds['center_lon']:.4f}, {bounds['center_lat']:.4f})")
            print(f"  面积: {area:.6f} 平方度")
            print(f"  坐标点数: {len(bounds['coordinates'])}")
            
            # 显示前几个坐标点
            print(f"  前5个坐标点:")
            for i, coord in enumerate(bounds['coordinates'][:5]):
                print(f"    {i+1}. ({coord[0]:.4f}, {coord[1]:.4f})")
    
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()
