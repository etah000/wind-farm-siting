# 性能测试
1. get data

- data source：[天地图](https://cloudcenter.tianditu.gov.cn/administrativeDivision)

2. coding

- 在wind/test目录下，生成一个python脚本，使用qgis,从geojson读取数据，获取其中一个行政区划的多边形范围。


3. design

文档是对于：有什么类似于[florsi](https://github.com/NatLabRockies/floris), [rev](https://github.com/NatLabRockies/reV)的开源项目吗，功能上，在指定的区域内
- 支持floris类似的风机排布优化
- 支持风机类型(一个风场，使用统一类型的风机)，风机个数，风机布局的统一优化。
- 支持输电接入点优化
- 可以分布式同时优化多个风电场，并对最终的结果进行对比分析 

"风电场布局优化技术方案调研文档.md"是一个概述文档，细化，修正或者扩展此文档，如果需要，请添加更多的方案，提供更详细、准确的描述和说明。