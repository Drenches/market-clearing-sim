"""
现货出清主算法模块
整合节点边际出清算法与网络模型
"""
from typing import Dict, List
from power_market_simulator.models.network import Network
from power_market_simulator.models.time_series import BidSegment
from power_market_simulator.algorithms.lmp_algorithm import run_clearing


class SpotMarketClearing:
    """现货市场出清系统"""
    
    def __init__(self, network: Network, bid_segments: Dict[str, List[BidSegment]] = None):
        self.network = network
        self.bid_segments = bid_segments
        self.lmp_results = {}
    
    def run_clearing(self) -> Dict[str, float]:
        """执行现货出清计算"""
        # 验证网络结构
        self._validate_network()
        
        # 执行节点边际出清算法
        self.lmp_results = run_clearing(self.network, self.bid_segments)
        
        return self.lmp_results
    
    def _validate_network(self):
        """验证网络结构的有效性"""
        # 检查是否有节点
        if not self.network.nodes:
            raise ValueError("网络中没有定义节点")
        
        # 检查是否有发电机
        if not self.network.generators:
            raise ValueError("网络中没有定义发电机")
        
        # 检查发电机是否都连接到有效节点
        for gen in self.network.generators.values():
            if gen.node_id not in self.network.nodes:
                raise ValueError(f"发电机 {gen.id} 连接到不存在的节点 {gen.node_id}")
        
        # 检查负荷是否都连接到有效节点
        for load in self.network.loads.values():
            if load.node_id not in self.network.nodes:
                raise ValueError(f"负荷 {load.id} 连接到不存在的节点 {load.node_id}")


def create_spot_market_clearing(network: Network, bid_segments: Dict[str, List[BidSegment]] = None) -> SpotMarketClearing:
    """创建现货市场出清实例"""
    return SpotMarketClearing(network, bid_segments)