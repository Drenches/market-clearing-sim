"""
Spot clearing main algorithm module
Integrating locational marginal clearing algorithm with network model
现货出清主算法模块
整合节点边际出清算法与网络模型
"""
from typing import Dict, List
from power_market_simulator.models.network import Network
from power_market_simulator.models.time_series import BidSegment
from power_market_simulator.algorithms.lmp_algorithm import run_clearing


class SpotMarketClearing:
    """Spot market clearing system
    现货市场出清系统
    """
    
    def __init__(self, network: Network, bid_segments: Dict[str, List[BidSegment]] = None):
        self.network = network
        self.bid_segments = bid_segments
        self.lmp_results = {}
    
    def run_clearing(self) -> Dict[str, float]:
        """Execute spot market clearing calculation
        执行现货出清计算
        """
        # Validate network structure
        # 验证网络结构
        self._validate_network()
        
        # Execute locational marginal clearing algorithm
        # 执行节点边际出清算法
        self.lmp_results = run_clearing(self.network, self.bid_segments)
        
        return self.lmp_results
    
    def _validate_network(self):
        """Validate network structure validity
        验证网络结构的有效性
        """
        # Check if there are nodes
        # 检查是否有节点
        if not self.network.nodes:
            raise ValueError("No nodes defined in network")
            raise ValueError("网络中没有定义节点")
        
        # Check if there are generators
        # 检查是否有发电机
        if not self.network.generators:
            raise ValueError("No generators defined in network")
            raise ValueError("网络中没有定义发电机")
        
        # Check if generators are all connected to valid nodes
        # 检查发电机是否都连接到有效节点
        for gen in self.network.generators.values():
            if gen.node_id not in self.network.nodes:
                raise ValueError(f"Generator {gen.id} connected to non-existent node {gen.node_id}")
                raise ValueError(f"发电机 {gen.id} 连接到不存在的节点 {gen.node_id}")
        
        # Check if loads are all connected to valid nodes
        # 检查负荷是否都连接到有效节点
        for load in self.network.loads.values():
            if load.node_id not in self.network.nodes:
                raise ValueError(f"Load {load.id} connected to non-existent node {load.node_id}")
                raise ValueError(f"负荷 {load.id} 连接到不存在的节点 {load.node_id}")


def create_spot_market_clearing(network: Network, bid_segments: Dict[str, List[BidSegment]] = None) -> SpotMarketClearing:
    """Create spot market clearing instance
    创建现货市场出清实例
    """
    return SpotMarketClearing(network, bid_segments)