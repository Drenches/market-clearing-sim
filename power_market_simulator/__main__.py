"""
现货出清系统演示程序
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from power_market_simulator.models.network import Network, Node, Generator, Load, TransmissionLine, GeneratorType
from power_market_simulator.models.time_series import create_sample_day_ahead_data
from power_market_simulator.algorithms import create_spot_market_clearing
from power_market_simulator.algorithms.time_series_lmp import run_time_series_clearing


def create_sample_network():
    """创建示例网络"""
    print("创建示例3节点网络...")
    
    # 创建测试网络 - 一个简单的3节点系统
    network = Network(name="Sample3BusSystem")
    
    # 添加3个节点
    network.add_node(Node(id="N1", name="广州节点", x=0, y=0))
    network.add_node(Node(id="N2", name="深圳节点", x=1, y=0))
    network.add_node(Node(id="N3", name="珠海节点", x=2, y=0))
    
    # 添加发电机
    network.add_generator(Generator(
        id="G1", 
        name="广州电厂1", 
        node_id="N1", 
        generator_type=GeneratorType.THERMAL,
        min_power=0.0, 
        max_power=300.0, 
        marginal_cost=280.0  # 火电边际成本
    ))
    
    network.add_generator(Generator(
        id="G2", 
        name="深圳电厂1", 
        node_id="N2", 
        generator_type=GeneratorType.THERMAL,
        min_power=0.0, 
        max_power=400.0, 
        marginal_cost=320.0
    ))
    
    network.add_generator(Generator(
        id="G3", 
        name="珠海电厂1", 
        node_id="N3", 
        generator_type=GeneratorType.HYDRO,
        min_power=0.0, 
        max_power=200.0, 
        marginal_cost=180.0  # 水电边际成本
    ))
    
    # 添加负荷
    network.add_load(Load(
        id="L1", 
        name="广州负荷", 
        node_id="N1", 
        demand=250.0
    ))
    
    network.add_load(Load(
        id="L2", 
        name="深圳负荷", 
        node_id="N2", 
        demand=350.0
    ))
    
    network.add_load(Load(
        id="L3", 
        name="珠海负荷", 
        node_id="N3", 
        demand=100.0
    ))
    
    # 添加输电线路
    network.add_line(TransmissionLine(
        id="L12", 
        name="广州-深圳线", 
        from_node="N1", 
        to_node="N2", 
        reactance=0.05,  # 线路电抗
        thermal_limit=200.0  # 热稳定极限
    ))
    
    network.add_line(TransmissionLine(
        id="L23", 
        name="深圳-珠海线", 
        from_node="N2", 
        to_node="N3", 
        reactance=0.08, 
        thermal_limit=150.0
    ))
    
    network.add_line(TransmissionLine(
        id="L13", 
        name="广州-珠海线", 
        from_node="N1", 
        to_node="N3", 
        reactance=0.10, 
        thermal_limit=120.0
    ))
    
    print("示例网络创建完成")
    print(f"节点数: {len(network.nodes)}")
    print(f"发电机数: {len(network.generators)}")
    print(f"负荷数: {len(network.loads)}")
    print(f"线路数: {len(network.lines)}")
    
    return network


def main():
    """主函数"""
    print("电力市场现货出清系统演示")
    print("=" * 40)
    
    # 创建示例网络
    network = create_sample_network()
    
    print("\n网络拓扑结构:")
    for node_id, node in network.nodes.items():
        gens = network.get_generators_at_node(node_id)
        loads = network.get_loads_at_node(node_id)
        connected_nodes = network.get_connected_nodes(node_id)
        
        print(f"  节点 {node_id}({node.name}):")
        print(f"    发电机: {[f'{g.id}({g.marginal_cost}元/MWh)' for g in gens]}")
        print(f"    负荷: {[f'{l.id}({l.demand}MW)' for l in loads]}")
        print(f"    连接节点: {connected_nodes}")
    
    print("\n执行现货出清计算...")
    
    # 创建出清系统实例
    clearing = create_spot_market_clearing(network)
    
    try:
        # 执行出清
        lmp_results = clearing.run_clearing()
        
        print("\n节点边际电价结果:")
        print("-" * 30)
        for node_id, price in lmp_results.items():
            node_name = network.nodes[node_id].name
            print(f"  {node_id}({node_name}): {price:.2f} 元/MWh")
        
        print("\n现货出清计算完成!")
        
    except Exception as e:
        print(f"出清计算出现错误: {e}")
        print("使用简化演示结果:")
        
        # 使用简化计算展示概念
        from power_market_simulator.algorithms.lmp_algorithm import LMPAlgorithm
        algorithm = LMPAlgorithm(network)
        simple_lmp = algorithm._calculate_simple_lmp()
        
        print("\n简化节点边际电价结果:")
        print("-" * 30)
        for node_id, price in simple_lmp.items():
            node_name = network.nodes[node_id].name
            print(f"  {node_id}({node_name}): {price:.2f} 元/MWh")
    
    print("\n" + "="*60)
    print("开始24小时时序仿真演示...")
    
    # 生成日前市场数据
    print("生成日前市场数据...")
    day_ahead_data = create_sample_day_ahead_data(network)
    
    # 执行24小时仿真
    print("执行24小时仿真...")
    hourly_results = run_time_series_clearing(day_ahead_data)
    
    print("\n24小时仿真结果摘要:")
    print("-" * 30)
    
    # 显示部分小时的结果
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
    
    print("\n24小时时序仿真演示完成!")


if __name__ == "__main__":
    main()

