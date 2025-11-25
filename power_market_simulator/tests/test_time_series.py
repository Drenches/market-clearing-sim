"""
时序仿真测试用例
"""
import unittest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from power_market_simulator.models.network import Network, Node, Generator, Load, TransmissionLine, GeneratorType
from power_market_simulator.models.time_series import create_sample_day_ahead_data, BidSegment
from power_market_simulator.algorithms.lmp_algorithm import LMPAlgorithm, run_clearing
from power_market_simulator.algorithms.time_series_lmp import run_time_series_clearing


class TestTimeSeriesSimulation(unittest.TestCase):
    """时序仿真系统测试"""
    
    def setUp(self):
        """设置测试网络"""
        # 创建测试网络 - 一个简单的3节点系统
        self.network = Network(name="TestTimeSeriesNetwork")
        
        # 添加3个节点
        self.network.add_node(Node(id="N1", name="Bus 1", x=0, y=0))
        self.network.add_node(Node(id="N2", name="Bus 2", x=1, y=0))
        self.network.add_node(Node(id="N3", name="Bus 3", x=2, y=0))
        
        # 添加发电机 - 传统火电
        self.network.add_generator(Generator(
            id="G1", 
            name="Thermal Gen 1", 
            node_id="N1", 
            generator_type=GeneratorType.THERMAL,
            min_power=0.0, 
            max_power=100.0, 
            marginal_cost=300.0
        ))
        
        # 添加新能源发电机
        self.network.add_generator(Generator(
            id="G2", 
            name="Wind Gen 1", 
            node_id="N2", 
            generator_type=GeneratorType.WIND,
            min_power=0.0, 
            max_power=80.0, 
            marginal_cost=50.0
        ))
        
        # 添加负荷
        self.network.add_load(Load(
            id="L1", 
            name="Load 1", 
            node_id="N1", 
            demand=70.0
        ))
        
        self.network.add_load(Load(
            id="L2", 
            name="Load 2", 
            node_id="N2", 
            demand=60.0
        ))
        
        # 添加输电线路
        self.network.add_line(TransmissionLine(
            id="L12", 
            name="Line 1-2", 
            from_node="N1", 
            to_node="N2", 
            reactance=0.1, 
            thermal_limit=100.0
        ))
    
    def test_bid_segment_creation(self):
        """测试分段报价创建"""
        # 创建分段报价
        seg1 = BidSegment(0, 30, 300.0)  # 前30MW报价300元/MWh
        seg2 = BidSegment(30, 70, 350.0)  # 30-70MW报价350元/MWh
        
        self.assertEqual(seg1.start_power, 0)
        self.assertEqual(seg1.end_power, 30)
        self.assertEqual(seg1.price, 300.0)
        self.assertEqual(seg1.capacity(), 30)
        
        self.assertEqual(seg2.capacity(), 40)
    
    def test_single_hour_clearing_with_segments(self):
        """测试单小时带分段报价的出清"""
        # 创建分段报价数据
        bid_segments = {
            "G1": [
                BidSegment(0, 30, 300.0),
                BidSegment(30, 60, 350.0),
                BidSegment(60, 100, 400.0)
            ]
        }
        
        # 执行出清
        results = run_clearing(self.network, bid_segments)
        
        # 检查结果
        self.assertIsNotNone(results)
        self.assertIn("N1", results)
        self.assertIn("N2", results)
        
        # N1节点应该有较高价格（火电出力）
        # N2节点应该有较低价格（风电出力）
        print(f"单小时出清结果: {results}")
    
    def test_day_ahead_data_creation(self):
        """测试日前数据创建"""
        day_ahead_data = create_sample_day_ahead_data(self.network)
        
        # 检查数据创建
        self.assertIsNotNone(day_ahead_data)
        self.assertEqual(len(day_ahead_data.generator_time_series), len(self.network.generators))
        self.assertEqual(len(day_ahead_data.load_time_series), len(self.network.loads))
        
        # 检查时序数据长度
        for gen_ts in day_ahead_data.generator_time_series.values():
            self.assertEqual(len(gen_ts.time_slots), 24)
        
        for load_ts in day_ahead_data.load_time_series.values():
            self.assertEqual(len(load_ts.time_slots), 24)
        
        print("日前数据创建成功")
    
    def test_hourly_network_extraction(self):
        """测试小时网络提取"""
        day_ahead_data = create_sample_day_ahead_data(self.network)
        
        # 提取第12小时的网络
        hourly_network = day_ahead_data.get_hourly_network(12)
        
        # 检查网络提取
        self.assertIsNotNone(hourly_network)
        self.assertEqual(len(hourly_network.nodes), len(self.network.nodes))
        
        # 检查发电机容量是否根据时序数据调整
        original_gen = self.network.generators["G2"]  # 风电机组
        hourly_gen = hourly_network.generators["G2"]
        
        # 风电机组容量应根据时序因子调整
        self.assertLessEqual(hourly_gen.max_power, original_gen.max_power)
        
        print(f"第12小时风电机组容量: {hourly_gen.max_power} MW (原容量: {original_gen.max_power} MW)")
    
    def test_24hour_simulation_basic(self):
        """测试24小时仿真基本功能"""
        day_ahead_data = create_sample_day_ahead_data(self.network)
        
        # 执行24小时仿真
        results = run_time_series_clearing(day_ahead_data)
        
        # 检查结果
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 24)  # 24小时
        
        # 检查每小时的结果
        for hour in range(24):
            self.assertIn(hour, results)
            hour_results = results[hour]
            self.assertIn("N1", hour_results)
            self.assertIn("N2", hour_results)
        
        print("24小时仿真基本功能测试通过")
        
        # 检查价格的合理性（不应有负价格）
        for hour in range(24):
            for node_id, price in results[hour].items():
                self.assertGreaterEqual(price, 0, f"小时 {hour}, 节点 {node_id} 出现负价格: {price}")


def run_tests():
    """运行所有测试"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()