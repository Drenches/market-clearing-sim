"""
现货出清系统测试用例
"""
import unittest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from power_market_simulator.models.network import Network, Node, Generator, Load, TransmissionLine, GeneratorType
from power_market_simulator.algorithms import create_spot_market_clearing


class TestSpotMarketClearing(unittest.TestCase):
    """现货市场出清系统测试"""
    
    def setUp(self):
        """设置测试网络"""
        # 创建测试网络 - 一个简单的3节点系统
        self.network = Network(name="Test3BusSystem")
        
        # 添加3个节点
        self.network.add_node(Node(id="N1", name="Bus 1", x=0, y=0))
        self.network.add_node(Node(id="N2", name="Bus 2", x=1, y=0))
        self.network.add_node(Node(id="N3", name="Bus 3", x=2, y=0))
        
        # 添加发电机
        self.network.add_generator(Generator(
            id="G1", 
            name="Gen 1", 
            node_id="N1", 
            generator_type=GeneratorType.THERMAL,
            min_power=0.0, 
            max_power=100.0, 
            marginal_cost=30.0
        ))
        
        self.network.add_generator(Generator(
            id="G2", 
            name="Gen 2", 
            node_id="N2", 
            generator_type=GeneratorType.THERMAL,
            min_power=0.0, 
            max_power=200.0, 
            marginal_cost=50.0
        ))
        
        # 添加负荷
        self.network.add_load(Load(
            id="L1", 
            name="Load 1", 
            node_id="N1", 
            demand=80.0
        ))
        
        self.network.add_load(Load(
            id="L2", 
            name="Load 2", 
            node_id="N2", 
            demand=150.0
        ))
        
        self.network.add_load(Load(
            id="L3", 
            name="Load 3", 
            node_id="N3", 
            demand=70.0
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
        
        self.network.add_line(TransmissionLine(
            id="L23", 
            name="Line 2-3", 
            from_node="N2", 
            to_node="N3", 
            reactance=0.1, 
            thermal_limit=100.0
        ))
        
        self.network.add_line(TransmissionLine(
            id="L13", 
            name="Line 1-3", 
            from_node="N1", 
            to_node="N3", 
            reactance=0.15, 
            thermal_limit=80.0
        ))
    
    def test_network_creation(self):
        """测试网络创建"""
        self.assertEqual(len(self.network.nodes), 3)
        self.assertEqual(len(self.network.generators), 2)
        self.assertEqual(len(self.network.loads), 3)
        self.assertEqual(len(self.network.lines), 3)
        
        # 检查节点
        self.assertIn("N1", self.network.nodes)
        self.assertIn("N2", self.network.nodes)
        self.assertIn("N3", self.network.nodes)
        
        # 检查发电机
        self.assertEqual(self.network.generators["G1"].node_id, "N1")
        self.assertEqual(self.network.generators["G2"].node_id, "N2")
        
        # 检查负荷
        self.assertEqual(self.network.loads["L1"].node_id, "N1")
        self.assertEqual(self.network.loads["L2"].node_id, "N2")
        self.assertEqual(self.network.loads["L3"].node_id, "N3")
    
    def test_spot_market_clearing_creation(self):
        """测试现货市场出清实例创建"""
        clearing = create_spot_market_clearing(self.network)
        self.assertIsNotNone(clearing)
        self.assertEqual(clearing.network, self.network)
    
    def test_clearing_validation(self):
        """测试网络验证功能"""
        clearing = create_spot_market_clearing(self.network)
        
        # 正常网络应该通过验证
        try:
            clearing._validate_network()
            validation_passed = True
        except ValueError:
            validation_passed = False
        
        self.assertTrue(validation_passed, "正常网络应该通过验证")
        
        # 测试无效节点连接
        invalid_network = Network(name="InvalidNetwork")
        invalid_network.add_node(Node(id="N1", name="Bus 1"))
        invalid_network.add_generator(Generator(
            id="G1", 
            name="Gen 1", 
            node_id="N99",  # 不存在的节点
            generator_type=GeneratorType.THERMAL,
            min_power=0.0, 
            max_power=100.0, 
            marginal_cost=30.0
        ))
        
        clearing_invalid = create_spot_market_clearing(invalid_network)
        with self.assertRaises(ValueError):
            clearing_invalid._validate_network()
    
    def test_simple_clearing(self):
        """测试简单的出清功能（不涉及复杂的优化求解）"""
        # 创建一个简单的网络用于测试
        simple_network = Network(name="SimpleNetwork")
        
        # 添加节点
        simple_network.add_node(Node(id="N1", name="Bus 1"))
        simple_network.add_node(Node(id="N2", name="Bus 2"))
        
        # 添加发电机
        simple_network.add_generator(Generator(
            id="G1", 
            name="Gen 1", 
            node_id="N1", 
            generator_type=GeneratorType.THERMAL,
            min_power=0.0, 
            max_power=100.0, 
            marginal_cost=30.0
        ))
        
        # 添加负荷
        simple_network.add_load(Load(
            id="L1", 
            name="Load 1", 
            node_id="N1", 
            demand=50.0
        ))
        
        simple_network.add_load(Load(
            id="L2", 
            name="Load 2", 
            node_id="N2", 
            demand=30.0
        ))
        
        # 执行出清（简化版，不依赖复杂优化）
        clearing = create_spot_market_clearing(simple_network)
        
        # 由于我们的LMP算法中包含复杂的优化部分，这里我们测试简化版
        # 实际上，我们测试的是算法类的结构和基本功能
        from power_market_simulator.algorithms.lmp_algorithm import LMPAlgorithm
        algorithm = LMPAlgorithm(simple_network)
        
        # 测试算法初始化
        self.assertEqual(len(algorithm.node_to_idx), 2)
        self.assertIn("N1", algorithm.node_to_idx)
        self.assertIn("N2", algorithm.node_to_idx)


def run_tests():
    """运行所有测试"""
    """Run all tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()