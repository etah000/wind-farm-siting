#!/usr/bin/env python3
"""
将 QGIS GeoJSON 坐标转换为 FLORIS 可用的格式

FLORIS 需要的是投影坐标系（笛卡尔坐标，单位：米）
而 GeoJSON 通常使用 WGS84（经纬度）

该脚本提供：
1. 从 GeoJSON 提取 MultiPolygon
2. 将经纬度转换为投影坐标（UTM）
3. 格式化为 FLORIS boundaries 所需的格式
"""

import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union

try:
    from pyproj import Transformer, CRS
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False
    print("警告: pyproj 未安装，将无法进行坐标转换")

try:
    from shapely.geometry import MultiPolygon, Polygon, shape
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("警告: shapely 未安装，将无法处理几何体")


class GeoJSONToFLORISConverter:
    """将 GeoJSON 坐标转换为 FLORIS 所需格式的转换器"""
    
    def __init__(self, geojson_path: str, target_crs: str = "EPSG:32650"):
        """
        初始化转换器
        
        Args:
            geojson_path: GeoJSON 文件路径
            target_crs: 目标投影坐标系（默认 UTM Zone 50N）
                       常见选项: "EPSG:32650" (UTM Zone 50N)
                                "EPSG:32649" (UTM Zone 49N)
                                "EPSG:4326" (WGS84, 如果不需要转换)
        """
        self.geojson_path = Path(geojson_path)
        self.target_crs = target_crs
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
    
    def get_utm_zone_from_coords(self, lon: float, lat: float) -> int:
        """
        根据经纬度计算 UTM 区号
        
        Args:
            lon: 经度
            lat: 纬度
            
        Returns:
            UTM 区号
        """
        zone = int((lon + 180) / 6) + 1
        return zone
    
    def degrees_to_utm_format(self, lon: float, lat: float) -> str:
        """
        将经纬度转换为 UTM EPSG 代码
        
        Args:
            lon: 经度
            lat: 纬度
            
        Returns:
            UTM EPSG 代码字符串，如 "EPSG:32650"
        """
        zone = self.get_utm_zone_from_coords(lon, lat)
        # 南半球 (32700+), 北半球 (32600+)
        epsg_code = 32600 + zone if lat >= 0 else 32700 + zone
        return f"EPSG:{epsg_code}"
    
    def get_centroid_from_feature(self, feature: Dict) -> Tuple[float, float]:
        """
        获取特征的中心点（经纬度）
        
        Args:
            feature: GeoJSON feature
            
        Returns:
            (经度, 纬度) 元组
        """
        if not SHAPELY_AVAILABLE:
            # 如果没有 shapely，使用简单的中心计算
            geom = feature.get('geometry', {})
            if geom.get('type') == 'Polygon':
                coords = geom['coordinates'][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                return (sum(lons) / len(lons), sum(lats) / len(lats))
        else:
            geom = shape(feature['geometry'])
            centroid = geom.centroid
            return (centroid.x, centroid.y)
    
    def convert_coordinates(self, lon: float, lat: float) -> Tuple[float, float]:
        """
        将单个点从经纬度转换为投影坐标
        
        Args:
            lon: 经度
            lat: 纬度
            
        Returns:
            (x, y) 投影坐标
        """
        if not PYPROJ_AVAILABLE:
            raise RuntimeError("需要安装 pyproj 来进行坐标转换")
        
        # 创建变压器
        transformer = Transformer.from_crs("EPSG:4326", self.target_crs, always_xy=True)
        x, y = transformer.transform(lon, lat)
        return (x, y)
    
    def convert_polygon_to_floris_format(self, feature_index: int, 
                                       auto_crs: bool = True) -> List[List[Tuple[float, float]]]:
        """
        将 GeoJSON 特征转换为 FLORIS boundaries 格式
        
        Args:
            feature_index: 特征索引
            auto_crs: 是否根据坐标自动选择 UTM 区号
            
        Returns:
            FLORIS boundaries 格式的坐标列表
        """
        if feature_index >= len(self.features):
            raise IndexError(f"特征索引超出范围: {feature_index}")
        
        feature = self.features[feature_index]
        geometry = feature.get('geometry', {})
        geom_type = geometry.get('type')
        
        if geom_type == 'Polygon':
            coordinates_list = [geometry.get('coordinates', [[]])]
        elif geom_type == 'MultiPolygon':
            coordinates_list = geometry.get('coordinates', [])
        else:
            raise ValueError(f"不支持的几何类型: {geom_type}")
        
        # 如果自动选择 CRS，从第一个点获取
        target_crs = self.target_crs
        if auto_crs and coordinates_list and coordinates_list[0]:
            first_point = coordinates_list[0][0][0]
            if isinstance(first_point, (list, tuple)) and len(first_point) >= 2:
                lon, lat = first_point[0], first_point[1]
                target_crs = self.degrees_to_utm_format(lon, lat)
                print(f"  自动选择 CRS: {target_crs}")
        
        # 设置转换器
        if auto_crs and target_crs != self.target_crs:
            self.target_crs = target_crs
        
        # 转换所有多边形
        converted_polygons = []
        for polygon_coords in coordinates_list:
            # polygon_coords 是外环 + 内环列表
            # 我们只取外环（第一个）
            exterior_ring = polygon_coords[0] if polygon_coords else []
            
            # 转换坐标
            converted_ring = []
            for lon, lat in exterior_ring:
                x, y = self.convert_coordinates(lon, lat)
                converted_ring.append((x, y))
            
            if converted_ring:
                converted_polygons.append(converted_ring)
        
        return converted_polygons
    
    def get_floris_boundaries(self, feature_index: int, 
                             combine_multipolygon: bool = False,
                             auto_crs: bool = True) -> Union[List[Tuple[float, float]], 
                                                              List[List[Tuple[float, float]]]]:
        """
        获取 FLORIS 可直接使用的 boundaries
        
        Args:
            feature_index: 特征索引
            combine_multipolygon: 是否将多个多边形合并为单环
            auto_crs: 是否根据坐标自动选择 UTM 区号
            
        Returns:
            如果是单个多边形，返回 [(x,y), (x,y), ...]
            如果是多个独立区域，返回 [[(x,y), ...], [(x,y), ...], ...]
        """
        polygons = self.convert_polygon_to_floris_format(feature_index, auto_crs=auto_crs)
        
        if len(polygons) == 1 or combine_multipolygon:
            # 返回单个多边形格式（适合大多数 FLORIS 优化算法）
            if combine_multipolygon and len(polygons) > 1:
                # 简单地连接所有多边形（可能不理想，仅用于演示）
                combined = []
                for poly in polygons:
                    combined.extend(poly)
                return combined
            return polygons[0]
        else:
            # 返回多个分离区域格式（如果支持）
            return polygons
    
    def list_features_info(self) -> List[Dict]:
        """列出所有特征的信息"""
        info_list = []
        for idx, feature in enumerate(self.features):
            geom_type = feature.get('geometry', {}).get('type', 'Unknown')
            props = feature.get('properties', {})
            
            # 获取几何体的中心点
            if SHAPELY_AVAILABLE:
                geom = shape(feature['geometry'])
                bounds = geom.bounds
                area = geom.area
            else:
                bounds = None
                area = None
            
            info = {
                'index': idx,
                'type': geom_type,
                'properties': props,
                'bounds': bounds,
                'area': area
            }
            info_list.append(info)
        
        return info_list


def main():
    """演示如何使用转换器"""
    print("=" * 70)
    print("GeoJSON to FLORIS Converter - 示例")
    print("=" * 70)
    
    geojson_file = Path(__file__).parent / "administrative_division.geojson"
    
    if not geojson_file.exists():
        print(f"\n❌ GeoJSON 文件不存在: {geojson_file}")
        print("\n使用说明:")
        print("1. 从天地图下载 GeoJSON 数据")
        print("2. 将文件保存为 administrative_division.geojson")
        print("3. 运行此脚本")
        return
    
    try:
        # 创建转换器实例
        # 注意：这里假设数据在 UTM Zone 50N (中国大部分地区)
        # 可根据实际坐标范围调整
        converter = GeoJSONToFLORISConverter(str(geojson_file))
        
        # 列出所有特征信息
        features_info = converter.list_features_info()
        print(f"\n共有 {len(features_info)} 个特征：\n")
        
        for info in features_info:
            print(f"  [{info['index']}] {info['type']}")
            if info['bounds']:
                print(f"       边界: {info['bounds']}")
                print(f"       面积: {info['area']:.2f}")
        
        # 转换第一个特征
        if features_info:
            feature_idx = 0
            print(f"\n{'=' * 70}")
            print(f"转换第 {feature_idx + 1} 个特征 ({features_info[feature_idx]['type']})...")
            print(f"{'=' * 70}\n")
            
            boundaries = converter.get_floris_boundaries(feature_idx, auto_crs=True)
            
            print(f"✓ 转换完成！")
            print(f"\n得到的 FLORIS boundaries 格式:")
            
            if isinstance(boundaries[0], (list, tuple)):
                # 多个多边形
                print(f"  多个分离区域: {len(boundaries)} 个多边形")
                for i, poly in enumerate(boundaries):
                    print(f"    多边形 {i+1}: {len(poly)} 个顶点")
                    print(f"      前 3 个顶点: {poly[:3]}")
            else:
                # 单个多边形
                print(f"  单个多边形: {len(boundaries)} 个顶点")
                print(f"\n  前 5 个顶点 (投影坐标, 米):")
                for i, (x, y) in enumerate(boundaries[:5]):
                    print(f"    {i+1}. ({x:.2f}, {y:.2f})")
            
            # 保存为 Python 代码供直接使用
            output_file = Path(__file__).parent / "floris_boundaries.py"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# FLORIS Layout Optimization Boundaries\n")
                f.write("# 从 GeoJSON 转换而来\n\n")
                f.write("boundaries = [\n")
                
                if isinstance(boundaries[0], (list, tuple)) and not isinstance(boundaries[0][0], (int, float)):
                    # 多个多边形
                    for poly in boundaries:
                        f.write("    [\n")
                        for x, y in poly:
                            f.write(f"        ({x:.2f}, {y:.2f}),\n")
                        f.write("    ],\n")
                else:
                    # 单个多边形
                    for x, y in boundaries:
                        f.write(f"    ({x:.2f}, {y:.2f}),\n")
                
                f.write("]\n")
            
            print(f"\n✓ 已保存到: {output_file}")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
