"""
自定义节点结构示例
展示如何创建自定义的电力网络结构
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from power_market_simulator.models.network import Network, Node, Generator, Load, TransmissionLine, GeneratorType
from power_market_simulator.algorithms import create_spot_market_clearing


def create_custom_network():
    """创建一个自定义的5节点网络模拟广东省电网"""
    print("创建自定义5节点网络模拟...")
    
    # 创建5节点网络，模拟广东省主要城市
    network = Network(name="GuangdongPowerGrid")
    
    # 添加5个节点，代表主要城市
    network.add_node(Node(id="GZ", name="广州节点", x=0, y=0))
    network.add_node(Node(id="SZ", name="深圳节点", x=1, y=0))
    network.add_node(Node(id="ZH", name="珠海节点", x=2, y=0))
    network.add_node(Node(id="FS", name="佛山节点", x=0, y=1))
    network.add_node(Node(id="DG", name="东莞节点", x=1, y=1))
    
    # 添加不同类型和容量的发电机
    # 广州节点
    network.add_generator(Generator(
        id="GZ_G1", 
        name="广州电厂1", 
        node_id="GZ", 
        generator_type=GeneratorType.THERMAL,
        min_power=50.0, 
        max_power=300.0, 
        marginal_cost=280.0  # 火电边际成本
    ))
    
    network.add_generator(Generator(
        id="GZ_G2", 
        name="广州电厂2", 
        node_id="GZ", 
        generator_type=GeneratorType.HYDRO,
        min_power=30.0, 
        max_power=150.0, 
        marginal_cost=180.0  # 水电边际成本较低
    ))
    
    # 深圳节点
    network.add_generator(Generator(
        id="SZ_G1", 
        name="深圳电厂1", 
        node_id="SZ", 
        generator_type=GeneratorType.THERMAL,
        min_power=40.0, 
        max_power=250.0, 
        marginal_cost=300.0
    ))
    
    # 珠海节点
    network.add_generator(Generator(
        id="ZH_G1", 
        name="珠海电厂1", 
        node_id="ZH", 
        generator_type=GeneratorType.WIND,
        min_power=0.0, 
        max_power=120.0, 
        marginal_cost=80.0  # 风电边际成本低
    ))
    
    # 佛山节点
    network.add_generator(Generator(
        id="FS_G1", 
        name="佛山电厂1", 
        node_id="FS", 
        generator_type=GeneratorType.THERMAL,
        min_power=60.0, 
        max_power=280.0, 
        marginal_cost=290.0
    ))
    
    # 东莞节点
    network.add_generator(Generator(
        id="DG_G1", 
        name="东莞电厂1", 
        node_id="DG", 
        generator_type=GeneratorType.SOLAR,
        min_power=0.0, 
        max_power=100.0, 
        marginal_cost=60.0  # 光伏边际成本最低
    ))
    
    # 添加负荷（模拟各城市用电需求）
    network.add_load(Load(
        id="GZ_L1", 
        name="广州负荷", 
        node_id="GZ", 
        demand=320.0  # 广州负荷较大
    ))
    
    network.add_load(Load(
        id="SZ_L1", 
        name="深圳负荷", 
        node_id="SZ", 
        demand=280.0  # 深圳负荷较大
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
        demand=250.0  # 佛山工业负荷较大
    ))
    
    network.add_load(Load(
        id="DG_L1", 
        name="东莞负荷", 
        node_id="DG", 
        demand=200.0  # 东莞工业负荷
    ))
    
    # 添加输电线路（模拟实际电网连接）
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
    
    network.add_line(TransmissionLine(
        id="SZ_DG", 
        name="深圳-东莞线", 
        from_node="SZ", 
        to_node="DG", 
        reactance=0.06, 
        thermal_limit=150.0
    ))
    
    print(f"自定义网络创建完成")
    print(f"节点数: {len(network.nodes)}")
    print(f"发电机数: {len(network.generators)}")
    print(f"负荷数: {len(network.loads)}")
    print(f"线路数: {len(network.lines)}")
    
    return network


def analyze_results(network, lmp_results):
    """分析出清结果"""
    print("\n详细分析结果:")
    print("=" * 50)
    
    total_demand = sum(load.demand for load in network.loads.values())
    total_supply = sum(gen.max_power for gen in network.generators.values())
    
    print(f"总负荷需求: {total_demand:.2f} MW")
    print(f"总发电能力: {total_supply:.2f} MW")
    print(f"供需比: {total_demand/total_supply:.2f}")
    
    print("\n各节点详细信息:")
    for node_id in network.nodes.keys():
        node = network.nodes[node_id]
        gens = network.get_generators_at_node(node_id)
        loads = network.get_loads_at_node(node_id)
        
        gen_capacity = sum(gen.max_power for gen in gens)
        total_load = sum(load.demand for load in loads)
        lmp = lmp_results[node_id]
        
        print(f"\n节点 {node_id}({node.name}):")
        print(f"  发电容量: {gen_capacity:.2f} MW")
        print(f"  负荷需求: {total_load:.2f} MW")
        print(f"  边际电价: {lmp:.2f} 元/MWh")
        print(f"  发电机: {[(gen.id, gen.marginal_cost) for gen in gens]}")
        print(f"  负荷: {[(load.id, load.demand) for load in loads]}")
        
        if gen_capacity < total_load:
            print(f"  状态: 电力短缺 ({total_load - gen_capacity:.2f} MW)")
        elif gen_capacity > total_load * 1.5:  # 如果容量远大于负荷
            print(f"  状态: 电力盈余")
        else:
            print(f"  状态: 供需基本平衡")
    
    # 计算系统指标
    avg_lmp = sum(lmp_results.values()) / len(lmp_results)
    max_lmp = max(lmp_results.values())
    min_lmp = min(lmp_results.values())
    
    print(f"\n系统指标:")
    print(f"  平均LMP: {avg_lmp:.2f} 元/MWh")
    print(f"  最高LMP: {max_lmp:.2f} 元/MWh")
    print(f"  最低LMP: {min_lmp:.2f} 元/MWh")
    print(f"  价格差异: {max_lmp - min_lmp:.2f} 元/MWh")


def main():
    """主函数"""
    print("电力市场现货出清系统 - 自定义节点结构示例")
    print("=" * 60)
    
    # 创建自定义网络
    network = create_custom_network()
    
    # 显示网络拓扑
    print("\n网络拓扑结构:")
    for node_id, node in network.nodes.items():
        connected_nodes = network.get_connected_nodes(node_id)
        gens = network.get_generators_at_node(node_id)
        loads = network.get_loads_at_node(node_id)
        
        print(f"  {node_id}({node.name}) -> {connected_nodes}")
        print(f"    发电机: {[(g.id, g.marginal_cost) for g in gens]}")
        print(f"    负荷: {[(l.id, l.demand) for l in loads]}")
    
    print("\n执行现货出清计算...")
    
    # 创建出清系统实例
    clearing = create_spot_market_clearing(network)
    
    try:
        # 执行出清
        lmp_results = clearing.run_clearing()
        
        print("\n节点边际电价结果:")
        print("-" * 40)
        for node_id, price in lmp_results.items():
            node_name = network.nodes[node_id].name
            print(f"  {node_id}({node_name}): {price:.2f} 元/MWh")
        
        # 分析结果
        analyze_results(network, lmp_results)
        
        print("\n现货出清计算完成!")
        
    except Exception as e:
        print(f"出清计算出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
