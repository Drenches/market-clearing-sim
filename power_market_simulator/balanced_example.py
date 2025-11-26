"""
电力市场仿真成功示例
展示一个发电容量充足、网络结构合理的例子，确保优化能够成功
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from power_market_simulator.models.network import Network, Node, Generator, Load, TransmissionLine, GeneratorType
from power_market_simulator.models.time_series import create_sample_day_ahead_data, BidSegment
from power_market_simulator.algorithms import create_spot_market_clearing
from power_market_simulator.algorithms.time_series_lmp import run_time_series_clearing


def create_balanced_network():
    """创建平衡的网络，确保发电容量大于负荷需求"""
    print("创建平衡的5节点网络...")
    
    network = Network(name="Balanced5BusSystem")
    
    # 添加5个节点
    network.add_node(Node(id="GZ", name="广州节点", x=0, y=0))
    network.add_node(Node(id="SZ", name="深圳节点", x=1, y=0))
    network.add_node(Node(id="ZH", name="珠海节点", x=2, y=0))
    network.add_node(Node(id="FS", name="佛山节点", x=0, y=1))
    network.add_node(Node(id="DG", name="东莞节点", x=1, y=1))
    
    # 添加充足的发电机
    # 广州节点 - 火电机组
    network.add_generator(Generator(
        id="GZ_G1", 
        name="广州火电厂1", 
        node_id="GZ", 
        generator_type=GeneratorType.THERMAL,
        min_power=20.0, 
        max_power=400.0, 
        marginal_cost=280.0
    ))
    
    # 深圳节点 - 火电机组
    network.add_generator(Generator(
        id="SZ_G1", 
        name="深圳火电厂1", 
        node_id="SZ", 
        generator_type=GeneratorType.THERMAL,
        min_power=20.0, 
        max_power=500.0, 
        marginal_cost=300.0
    ))
    
    # 珠海节点 - 水电机组和风电机组
    network.add_generator(Generator(
        id="ZH_G1", 
        name="珠海水电厂1", 
        node_id="ZH", 
        generator_type=GeneratorType.HYDRO,
        min_power=10.0, 
        max_power=200.0, 
        marginal_cost=180.0
    ))
    
    network.add_generator(Generator(
        id="ZH_G2", 
        name="珠海风电场1", 
        node_id="ZH", 
        generator_type=GeneratorType.WIND,
        min_power=0.0, 
        max_power=150.0, 
        marginal_cost=50.0
    ))
    
    # 佛山节点 - 火电机组
    network.add_generator(Generator(
        id="FS_G1", 
        name="佛山火电厂1", 
        node_id="FS", 
        generator_type=GeneratorType.THERMAL,
        min_power=20.0, 
        max_power=300.0, 
        marginal_cost=290.0
    ))
    
    # 东莞节点 - 光伏机组和火电机组
    network.add_generator(Generator(
        id="DG_G1", 
        name="东莞光伏电站1", 
        node_id="DG", 
        generator_type=GeneratorType.SOLAR,
        min_power=0.0, 
        max_power=100.0, 
        marginal_cost=40.0
    ))
    
    network.add_generator(Generator(
        id="DG_G2", 
        name="东莞火电厂1", 
        node_id="DG", 
        generator_type=GeneratorType.THERMAL,
        min_power=15.0, 
        max_power=250.0, 
        marginal_cost=310.0
    ))
    
    # 添加负荷（确保总负荷小于总发电容量）
    network.add_load(Load(
        id="GZ_L1", 
        name="广州负荷", 
        node_id="GZ", 
        demand=180.0
    ))
    
    network.add_load(Load(
        id="SZ_L1", 
        name="深圳负荷", 
        node_id="SZ", 
        demand=250.0
    ))
    
    network.add_load(Load(
        id="ZH_L1", 
        name="珠海负荷", 
        node_id="ZH", 
        demand=120.0
    ))
    
    network.add_load(Load(
        id="FS_L1", 
        name="佛山负荷", 
        node_id="FS", 
        demand=150.0
    ))
    
    network.add_load(Load(
        id="DG_L1", 
        name="东莞负荷", 
        node_id="DG", 
        demand=180.0
    ))
    
    # 添加输电线路
    network.add_line(TransmissionLine(
        id="GZ_SZ", 
        name="广州-深圳线", 
        from_node="GZ", 
        to_node="SZ", 
        reactance=0.02, 
        thermal_limit=400.0
    ))
    
    network.add_line(TransmissionLine(
        id="SZ_ZH", 
        name="深圳-珠海线", 
        from_node="SZ", 
        to_node="ZH", 
        reactance=0.03, 
        thermal_limit=300.0
    ))
    
    network.add_line(TransmissionLine(
        id="GZ_FS", 
        name="广州-佛山线", 
        from_node="GZ", 
        to_node="FS", 
        reactance=0.02, 
        thermal_limit=350.0
    ))
    
    network.add_line(TransmissionLine(
        id="GZ_DG", 
        name="广州-东莞线", 
        from_node="GZ", 
        to_node="DG", 
        reactance=0.04, 
        thermal_limit=300.0
    ))
    
    network.add_line(TransmissionLine(
        id="FS_DG", 
        name="佛山-东莞线", 
        from_node="FS", 
        to_node="DG", 
        reactance=0.03, 
        thermal_limit=250.0
    ))
    
    print(f"网络创建完成")
    print(f"节点数: {len(network.nodes)}")
    print(f"发电机数: {len(network.generators)}")
    print(f"负荷数: {len(network.loads)}")
    print(f"线路数: {len(network.lines)}")
    
    total_gen_capacity = sum(g.max_power for g in network.generators.values())
    total_load = sum(l.demand for l in network.loads.values())
    print(f"总发电容量: {total_gen_capacity:.2f} MW")
    print(f"总负荷需求: {total_load:.2f} MW")
    print(f"容量充裕度: {total_gen_capacity/total_load:.2f} 倍")
    
    return network


def create_bid_segments():
    """创建分段报价数据"""
    bid_segments = {}
    
    # 为火电机组创建分段报价
    for gen_id in ["GZ_G1", "SZ_G1", "FS_G1", "DG_G2"]:
        bid_segments[gen_id] = [
            BidSegment(0, 100, 280.0),  # 前100MW报价280元/MWh
            BidSegment(100, 200, 300.0), # 100-200MW报价300元/MWh
            BidSegment(200, 300, 320.0), # 200-300MW报价320元/MWh
            BidSegment(300, 400, 340.0)  # 300-400MW报价340元/MWh
        ]
        
    # 为水电和新能源机组设置较低报价
    bid_segments["ZH_G1"] = [  # 水电机组
        BidSegment(0, 100, 180.0),
        BidSegment(100, 200, 200.0)
    ]
    
    bid_segments["ZH_G2"] = [  # 风电机组
        BidSegment(0, 150, 50.0)  # 风电报价很低
    ]
    
    bid_segments["DG_G1"] = [  # 光伏机组
        BidSegment(0, 100, 40.0)  # 光伏报价最低
    ]
    
    return bid_segments


def main():
    """主函数"""
    print("电力市场成功仿真演示")
    print("=" * 50)
    
    # 创建平衡的网络
    network = create_balanced_network()
    
    print("\n执行带分段报价的现货出清...")
    
    # 创建分段报价数据
    bid_segments = create_bid_segments()
    
    # 创建出清系统实例
    clearing = create_spot_market_clearing(network, bid_segments)
    
    try:
        # 执行出清
        lmp_results = clearing.run_clearing()
        
        print("\n节点边际电价结果:")
        print("-" * 30)
        for node_id, price in lmp_results.items():
            node_name = network.nodes[node_id].name
            print(f"  {node_id}({node_name}): {price:.2f} 元/MWh")
        
        print("\n现货出清计算成功!")
        
    except Exception as e:
        print(f"出清计算出现错误: {e}")
        return
    
    print("\n" + "="*60)
    print("开始24小时时序仿真演示...")
    
    # 生成日前市场数据
    print("生成日前市场数据...")
    day_ahead_data = create_sample_day_ahead_data(network)
    
    # 执行24小时仿真
    print("执行24小时时序仿真...")
    hourly_results = run_time_series_clearing(day_ahead_data)
    
    print("\n24小时仿真结果摘要:")
    print("-" * 30)
    
    # 显示特定小时的结果
    import pdb; pdb.set_trace()
    for hour in [6, 12, 18]:  # 早高峰、平段、晚高峰
        print(f"\n{hour:02d}时节点电价:")
        for node_id, price in hourly_results[hour].items():
            node_name = network.nodes[node_id].name
            print(f"  {node_id}({node_name}): {price:.2f} 元/MWh")
    
    # 计算各节点日平均价格
    print(f"\n各节点日平均价格:")
    for node_id in hourly_results[0].keys():
        avg_price = sum(hourly_results[h][node_id] for h in range(24)) / 24
        print(f"  {node_id}: {avg_price:.2f} 元/MWh")
    
    print("\n24小时时序仿真演示成功完成!")


if __name__ == "__main__":
    main()
