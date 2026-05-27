#!/usr/bin/env python3
"""
使用 osmium/GDAL 读取 OpenStreetMap OSM 文件

该脚本演示：
1. 使用 osmium 或 GDAL/OGR 读取 OSM PBF 文件
2. 提取不同类型的几何体（点、线、多边形）
3. 显示 OSM 标签和特征类型（如"住宅区"、"工厂"等）
4. 统计不同类型的地物信息

OSM 文件中常见的标签类型：
- building: 建筑物
- landuse: 土地用途（residential/industrial/commercial 等）
- highway: 道路
- railway: 铁路
- amenity: 公共设施
- natural: 自然特征
"""

import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

try:
    import osmium
    OSMIUM_AVAILABLE = True
except ImportError:
    OSMIUM_AVAILABLE = False

try:
    from osgeo import gdal, ogr
    gdal.UseExceptions()
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False

if not (OSMIUM_AVAILABLE or GDAL_AVAILABLE):
    print("❌ 错误: 需要 osmium 或 GDAL/OGR")
    print("   请运行: pip install osmium")
    print("    或: conda install gdal")
    sys.exit(1)

class OSMAnalyzer:
    """分析 OSM 文件的几何类型和标签信息"""
    
    # 常见的 OSM 标签，用于识别特征类型
    FEATURE_TYPES = {
        'building': '建筑物',
        'residential': '住宅区',
        'industrial': '工业区',
        'commercial': '商业区',
        'park': '公园',
        'forest': '森林',
        'farmland': '农地',
        'water': '水体',
        'highway': '道路',
        'railway': '铁路',
        'amenity': '公共设施',
        'landuse': '土地用途',
        'natural': '自然特征',
    }
    
    def __init__(self, osm_file_path: str):
        """
        初始化 OSM 分析器
        
        Args:
            osm_file_path: OSM PBF 文件路径
        """
        self.osm_file_path = Path(osm_file_path)
        if not self.osm_file_path.exists():
            raise FileNotFoundError(f"OSM 文件不存在: {self.osm_file_path}")
        
        # 确定使用哪个库
        self.use_osmium = OSMIUM_AVAILABLE
        self.use_gdal = GDAL_AVAILABLE and not self.use_osmium
        
        if self.use_osmium:
            print(f"✓ 使用 osmium 库")
        elif self.use_gdal:
            print(f"✓ 使用 GDAL/OGR 库")
        
        self.stats = defaultdict(lambda: {
            'count': 0,
            'geometry_types': defaultdict(int),
            'tags': defaultdict(int),
        })
    
    def analyze_with_osmium(self, max_features: int = None):
        """使用 osmium 分析 OSM 文件"""
        print(f"\n读取 OSM 文件: {self.osm_file_path}")
        print("-" * 80)
        
        class OSMHandler(osmium.SimpleHandler):
            def __init__(self):
                super().__init__()
                self.nodes_count = 0
                self.ways_count = 0
                self.relations_count = 0
                self.node_tags = defaultdict(lambda: defaultdict(int))
                self.way_tags = defaultdict(lambda: defaultdict(int))
                self.relation_tags = defaultdict(lambda: defaultdict(int))
                self.samples = {'nodes': [], 'ways': [], 'relations': []}
                self.max_features = max_features
            
            def node(self, n):
                if self.max_features and self.nodes_count >= self.max_features:
                    return
                self.nodes_count += 1
                # osmium uses TagList, not dict
                for key, value in n.tags:
                    self.node_tags[key][value] += 1
                if len(self.samples['nodes']) < 5:
                    self.samples['nodes'].append({
                        'id': n.id,
                        'lat': n.lat,
                        'lon': n.lon,
                        'type': 'Point',
                        'tags': dict(n.tags)
                    })
            
            def way(self, w):
                if self.max_features and self.ways_count >= self.max_features:
                    return
                self.ways_count += 1
                # osmium uses TagList, not dict
                for key, value in w.tags:
                    self.way_tags[key][value] += 1
                if len(self.samples['ways']) < 5:
                    try:
                        nodes_count = len(list(w.nd_list()))
                    except:
                        nodes_count = 0
                    self.samples['ways'].append({
                        'id': w.id,
                        'type': 'LineString/Polygon',
                        'nodes_count': nodes_count,
                        'tags': dict(w.tags)
                    })
            
            def relation(self, r):
                if self.max_features and self.relations_count >= self.max_features:
                    return
                self.relations_count += 1
                # osmium uses TagList, not dict
                for key, value in r.tags:
                    self.relation_tags[key][value] += 1
                if len(self.samples['relations']) < 5:
                    self.samples['relations'].append({
                        'id': r.id,
                        'type': 'Relation',
                        'members_count': len(r.members),
                        'tags': dict(r.tags)
                    })
        
        handler = OSMHandler()
        handler.apply_file(str(self.osm_file_path))
        
        return {
            'nodes_count': handler.nodes_count,
            'ways_count': handler.ways_count,
            'relations_count': handler.relations_count,
            'node_tags': dict(handler.node_tags),
            'way_tags': dict(handler.way_tags),
            'relation_tags': dict(handler.relation_tags),
            'samples': handler.samples,
        }
    
    def analyze_with_gdal(self, max_features: int = None) -> Dict:
        """使用 GDAL/OGR 分析 OSM 文件"""
        print(f"\n打开 OSM 文件: {self.osm_file_path}")
        
        datasource = ogr.Open(str(self.osm_file_path))
        if datasource is None:
            raise RuntimeError(f"无法打开 OSM 文件: {self.osm_file_path}")
        
        layer_count = datasource.GetLayerCount()
        print(f"✓ 找到 {layer_count} 个图层")
        print("-" * 80)
        
        all_results = {}
        
        for layer_idx in range(layer_count):
            layer = datasource.GetLayer(layer_idx)
            layer_name = layer.GetName()
            feature_count = layer.GetFeatureCount()
            
            print(f"\n分析图层: '{layer_name}' (总特征数: {feature_count})")
            
            geometry_types = defaultdict(int)
            tags_info = defaultdict(lambda: defaultdict(int))
            sample_features = []
            
            layer.ResetReading()
            for i, feature in enumerate(layer):
                if max_features and i >= max_features:
                    break
                
                geom = feature.GetGeometryRef()
                if geom is not None:
                    geom_type = geom.GetGeometryName()
                    geometry_types[geom_type] += 1
                
                # 提取标签
                tags_dict = {}
                field_count = feature.GetFieldCount()
                for j in range(field_count):
                    field_def = feature.GetFieldDefnRef(j)
                    field_name = field_def.GetName()
                    field_value = feature.GetField(j)
                    tags_dict[field_name] = field_value
                    
                    if field_value is not None:
                        tags_info[field_name][str(field_value)] += 1
                
                if len(sample_features) < 5:
                    sample_features.append({
                        'id': i,
                        'type': geom.GetGeometryName() if geom else 'Unknown',
                        'tags': tags_dict
                    })
            
            all_results[layer_name] = {
                'feature_count': feature_count,
                'analyzed_features': min(feature_count, max_features or feature_count),
                'geometry_types': dict(geometry_types),
                'tags_info': dict(tags_info),
                'sample_features': sample_features,
            }
        
        return all_results
    
    def analyze(self, max_features: int = 100) -> Dict:
        """
        分析 OSM 文件
        
        Args:
            max_features: 每种类型最多分析的特征数
        
        Returns:
            分析结果字典
        """
        if self.use_osmium:
            return self.analyze_with_osmium(max_features)
        elif self.use_gdal:
            return self.analyze_with_gdal(max_features)
        else:
            raise RuntimeError("没有可用的 OSM 读取库")
    
    def print_osmium_results(self, analysis: Dict):
        """打印 osmium 分析结果"""
        print(f"\n📊 OSM 对象统计:")
        print(f"  • 节点 (Nodes): {analysis['nodes_count']}")
        print(f"  • 路线 (Ways): {analysis['ways_count']}")
        print(f"  • 关系 (Relations): {analysis['relations_count']}")
        print(f"  • 总计: {analysis['nodes_count'] + analysis['ways_count'] + analysis['relations_count']}")
        
        print(f"\n🏷️  节点标签 (top 15):")
        node_tags = sorted(
            analysis['node_tags'].items(),
            key=lambda x: sum(x[1].values()),
            reverse=True
        )[:15]
        for tag_name, values in node_tags:
            total = sum(values.values())
            top_values = sorted(values.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"\n  {tag_name} (总计: {total}):")
            for value, count in top_values:
                display_value = value if len(value) < 30 else value[:27] + "..."
                print(f"    - {display_value}: {count}")
        
        print(f"\n🏷️  路线标签 (top 15):")
        way_tags = sorted(
            analysis['way_tags'].items(),
            key=lambda x: sum(x[1].values()),
            reverse=True
        )[:15]
        for tag_name, values in way_tags:
            total = sum(values.values())
            top_values = sorted(values.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"\n  {tag_name} (总计: {total}):")
            for value, count in top_values:
                display_value = value if len(value) < 30 else value[:27] + "..."
                print(f"    - {display_value}: {count}")
        
        print(f"\n🏷️  关系标签 (top 10):")
        relation_tags = sorted(
            analysis['relation_tags'].items(),
            key=lambda x: sum(x[1].values()),
            reverse=True
        )[:10]
        for tag_name, values in relation_tags:
            total = sum(values.values())
            top_values = sorted(values.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"\n  {tag_name} (总计: {total}):")
            for value, count in top_values:
                display_value = value if len(value) < 30 else value[:27] + "..."
                print(f"    - {display_value}: {count}")
        
        # 打印示例
        print(f"\n📍 示例对象:")
        for category in ['nodes', 'ways', 'relations']:
            samples = analysis['samples'][category]
            if samples:
                print(f"\n  {category.upper()}:")
                for sample in samples[:3]:
                    print(f"    ID: {sample['id']}, 类型: {sample['type']}")
                    for tag_key in list(sample['tags'].keys())[:3]:
                        tag_value = sample['tags'][tag_key]
                        display_value = str(tag_value)[:40]
                        print(f"      • {tag_key}: {display_value}")
    
    def print_gdal_results(self, analysis: Dict):
        """打印 GDAL 分析结果"""
        print(f"\n📊 图层统计:")
        for layer_name, layer_analysis in analysis.items():
            print(f"\n  {layer_name}:")
            print(f"    总特征数: {layer_analysis['feature_count']}")
            print(f"    已分析: {layer_analysis['analyzed_features']}")
            
            print(f"    几何类型: {', '.join(layer_analysis['geometry_types'].keys())}")
            for geom_type, count in layer_analysis['geometry_types'].items():
                print(f"      • {geom_type}: {count}")
            
            tags_info = layer_analysis['tags_info']
            if tags_info:
                print(f"    标签统计 (前 5 个):")
                for tag_name in sorted(tags_info.keys())[:5]:
                    values = tags_info[tag_name]
                    top_values = sorted(values.items(), key=lambda x: x[1], reverse=True)[:3]
                    print(f"      {tag_name}:")
                    for value, count in top_values:
                        display_value = value if len(value) < 30 else value[:27] + "..."
                        print(f"        - {display_value}: {count}")


def main():
    """主程序"""
    print("=" * 80)
    print("🗺️  OSM 文件分析工具 - 使用 osmium/GDAL")
    print("=" * 80)
    
    # 查找 OSM 文件
    osm_file = Path(__file__).parent.parent / "data" / "beijing-260416.osm.pbf"
    
    if not osm_file.exists():
        print(f"\n❌ OSM 文件不存在: {osm_file}")
        print(f"\n📁 请确保文件位于: {osm_file}")
        sys.exit(1)
    
    print(f"\n📍 目标文件: {osm_file}")
    print(f"📊 文件大小: {osm_file.stat().st_size / (1024*1024):.2f} MB")
    
    # 创建分析器
    try:
        analyzer = OSMAnalyzer(str(osm_file))
        
        # 分析 OSM 文件
        max_features = 100
        print(f"\n⏳ 分析文件（限制每类型最多 {max_features} 个对象）...")
        
        analysis = analyzer.analyze(max_features=max_features)
        
        # 打印结果
        if analyzer.use_osmium:
            analyzer.print_osmium_results(analysis)
        elif analyzer.use_gdal:
            analyzer.print_gdal_results(analysis)
        
        print("\n✅ 分析完成!")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
