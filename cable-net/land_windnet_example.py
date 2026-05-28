from pathlib import Path

import numpy as np
from optiwindnet.api import EWRouter, MILPRouter, ModelOptions, WindFarmNetwork


def main() -> None:
    # 陆地风电场布局（坐标单位：米，UTM 平面坐标）
    turbinesC = np.array(
        [
            [1000, 2000],
            [1500, 2000],
            [2000, 2000],
            [1000, 2500],
            [1500, 2500],
            [2000, 2500],
            [1000, 3000],
            [1500, 3000],
            [2000, 3000],
            [1500, 3500],
        ],
        dtype=float,
    )

    substationsC = np.array([[1500, 1000]], dtype=float)

    # 风电场边界（逆时针多边形）
    borderC = np.array(
        [
            [500, 500],
            [2500, 500],
            [2500, 4000],
            [500, 4000],
        ],
        dtype=float,
    )

    # 障碍物（如公路用地，顺时针多边形）
    road = np.array(
        [
            [1200, 2200],
            [1800, 2200],
            [1800, 2300],
            [1200, 2300],
        ],
        dtype=float,
    )

    # 电缆规格：[(最大接入风机数, 单位长度造价), ...]
    cables = [(3, 1.0), (6, 1.4), (10, 1.8)]

    wfn = WindFarmNetwork(
        cables=cables,
        turbinesC=turbinesC,
        substationsC=substationsC,
        borderC=borderC,
        obstacleC_=[road],
        name="示例陆地风电场",
    )

    # 快速启发式求解（毫秒级）
    wfn.optimize(router=EWRouter())
    print(f"EWRouter 总长度: {wfn.length():.0f} 米, 总造价: {wfn.cost():.2f}")

    # 精确 MILP 求解（以 EWRouter 解作为热启动）
    milp = MILPRouter(
        solver_name="ortools.cp_sat",
        time_limit=30,
        mip_gap=0.005,
        model_options=ModelOptions(topology="branched", feeder_limit="minimum"),
    )
    wfn.optimize(router=milp)
    print(f"MILPRouter 总长度: {wfn.length():.0f} 米, 总造价: {wfn.cost():.2f}")
    print(wfn.solution_info())

    # OptiWindNet 的 plot() 返回 SvgRepr，直接保存为 SVG 文件
    output_path = Path(__file__).with_name("land_windnet_example.svg")
    wfn.plot().save(output_path)
    print(f"图已保存到: {output_path}")


if __name__ == "__main__":
    main()
