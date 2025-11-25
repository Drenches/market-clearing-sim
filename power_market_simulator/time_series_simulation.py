"""
24小时时序仿真演示程序
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from power_market_simulator.models.network import Network, Node, Generator, Load, TransmissionLine, GeneratorType
from power_market_simulator.models.time_series import create_sample_day_ahead_data
from power_market_simulator.algorithms.time_series_lmp import run_time_series_clearing


def create_sample_network():
    """创建示例网络"""
    print("创建示例5节点网络用于24小时仿真...")
    
    # 创建5节点网络，模拟广东省主要城市
    network = Network(name="Guangdong24hSimulation")
    
    # 添加5个节点，代表主要城市
    network.add_node(Node(id="GZ", name="广州节点", x=0, y=0))
    network.add_node(Node(id="SZ", name="深圳节点", x=1, y=0))
    network.add_node(Node(id="ZH", name="珠海节点", x=2, y=0))
    network.add_node(Node(id="FS", name="佛山节点", x=0, y=1))
    network.add_node(Node(id="DG", name="东莞节点", x=1, y=1))
    
    # 添加不同类型和容量的发电机
    # 广州节点 - 火电机组
    network.add_generator(Generator(
        id="GZ_G1", 
        name="广州火电厂1", 
        node_id="GZ", 
        generator_type=GeneratorType.THERMAL,
        min_power=50.0, 
        max_power=300.0, 
        marginal_cost=280.0
    ))
    
    # 深圳节点 - 火电机组
    network.add_generator(Generator(
        id="SZ_G1", 
        name="深圳火电厂1", 
        node_id="SZ", 
        generator_type=GeneratorType.THERMAL,
        min_power=40.0, 
        max_power=250.0, 
        marginal_cost=300.0
    ))
    
    # 珠海节点 - 风电机组
    network.add_generator(Generator(
        id="ZH_G1", 
        name="珠海风电场1", 
        node_id="ZH", 
        generator_type=GeneratorType.WIND,
        min_power=0.0, 
        max_power=120.0, 
        marginal_cost=80.0
    ))
    
    # 佛山节点 - 火电机组
    network.add_generator(Generator(
        id="FS_G1", 
        name="佛山火电厂1", 
        node_id="FS", 
        generator_type=GeneratorType.THERMAL,
        min_power=60.0, 
        max_power=280.0, 
        marginal_cost=290.0
    ))
    
    # 东莞节点 - 光伏机组
    network.add_generator(Generator(
        id="DG_G1", 
        name="东莞光伏电站1", 
        node_id="DG", 
        generator_type=GeneratorType.SOLAR,
        min_power=0.0, 
        max_power=100.0, 
        marginal_cost=60.0
    ))
    
    # 添加负荷（模拟各城市用电需求）
    network.add_load(Load(
        id="GZ_L1", 
        name="广州负荷", 
        node_id="GZ", 
        demand=320.0
    ))
    
    network.add_load(Load(
        id="SZ_L1", 
        name="深圳负荷", 
        node_id="SZ", 
        demand=280.0
    ))
    
    network.add_load(Load(
        id="ZH_L1", 
        name="珠海负荷", 
        node_id="ZH", 
        demand=90.0
    ))
    
    network.add_load(Load(
        id="FS_L1", 
        name="佛山负荷", 
        node_id="FS", 
        demand=250.0
    ))
    
    network.add_load(Load(
        id="DG_L1", 
        name="东莞负荷", 
        node_id="DG", 
        demand=200.0
    ))
    
    # 添加输电线路
    network.add_line(TransmissionLine(
        id="GZ_SZ", 
        name="广州-深圳线", 
        from_node="GZ", 
        to_node="SZ", 
        reactance=0.03, 
        thermal_limit=300.0
    ))
    
    network.add_line(TransmissionLine(
        id="SZ_ZH", 
        name="深圳-珠海线", 
        from_node="SZ", 
        to_node="ZH", 
        reactance=0.05, 
        thermal_limit=200.0
    ))
    
    network.add_line(TransmissionLine(
        id="GZ_FS", 
        name="广州-佛山线", 
        from_node="GZ", 
        to_node="FS", 
        reactance=0.02, 
        thermal_limit=250.0
    ))
    
    network.add_line(TransmissionLine(
        id="GZ_DG", 
        name="广州-东莞线", 
        from_node="GZ", 
        to_node="DG", 
        reactance=0.04, 
        thermal_limit=220.0
    ))
    
    network.add_line(TransmissionLine(
        id="FS_DG", 
        name="佛山-东莞线", 
        from_node="FS", 
        to_node="DG", 
        reactance=0.03, 
        thermal_limit=180.0
    ))
    
    print(f"示例网络创建完成")
    print(f"节点数: {len(network.nodes)}")
    print(f"发电机数: {len(network.generators)}")
    print(f"负荷数: {len(network.loads)}")
    print(f"线路数: {len(network.lines)}")
    
    return network


def analyze_24h_results(hourly_results):
    """分析24小时仿真结果"""
    print("\n24小时仿真结果分析:")
    print("=" * 60)
    
    # 按小时展示结果
    for hour in range(24):
        print(f"\n第{hour:02d}时结果:")
        for node_id, price in hourly_results[hour].items():
            print(f"  {node_id}: {price:.2f} 元/MWh")
    
    # 计算各节点的日平均价格
    print(f"\n各节点日平均价格:")
    node_hours = list(hourly_results[0].keys())
    for node_id in node_hours:
        avg_price = sum(hourly_results[h][node_id] for h in range(24)) / 24
        min_price = min(hourly_results[h][node_id] for h in range(24))
        max_price = max(hourly_results[h][node_id] for h in range(24))
        print(f"  {node_id}: 平均{avg_price:.2f}, 最低{min_price:.2f}, 最高{max_price:.2f}")
    
    # 识别高峰和低谷时段
    print(f"\n系统整体分析:")
    system_avg_prices = []
    for hour in range(24):
        avg_price = sum(hourly_results[hour].values()) / len(hourly_results[hour])
        system_avg_prices.append(avg_price)
        print(f"  {hour:02d}时系统平均价格: {avg_price:.2f} 元/MWh")
    
    peak_hour = system_avg_prices.index(max(system_avg_prices))
    off_peak_hour = system_avg_prices.index(min(system_avg_prices))
    print(f"\n  日内最高电价时段: {peak_hour:02d}时 ({max(system_avg_prices):.2f}元/MWh)")
    print(f"  日内最低电价时段: {off_peak_hour:02d}时 ({min(system_avg_prices):.2f}元/MWh)")


def main():
    """主函数"""
    print("电力市场24小时时序仿真系统")
    print("=" * 50)
    
    # 创建示例网络
    network = create_sample_network()
    
    print("\n生成日前市场数据...")
    day_ahead_data = create_sample_day_ahead_data(network)
    
    print("开始执行24小时时序仿真...")
    
    # 执行24小时仿真
    hourly_results = run_time_series_clearing(day_ahead_data)
    
    print("\n24小时仿真完成!")
    
    # 分析结果
    analyze_24h_results(hourly_results)
    
    print("\n仿真分析完成!")


if __name__ == "__main__":
    main()
