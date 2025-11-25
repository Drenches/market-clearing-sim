"""
24小时时序仿真算法
扩展节点边际出清算法以支持时序仿真和分段报价
"""
import numpy as np
from typing import Dict, List, Tuple
from scipy.optimize import linprog
from power_market_simulator.models.network import Network, Generator, Load
from power_market_simulator.models.time_series import DayAheadMarketData, BidSegment
from power_market_simulator.algorithms.lmp_algorithm import LMPAlgorithm


class TimeSeriesLMPAlgorithm:
    """时序节点边际电价算法类"""
    
    def __init__(self, day_ahead_data: DayAheadMarketData):
        self.day_ahead_data = day_ahead_data
        self.hourly_results = {}  # 存储每小时的计算结果
    
    def calculate_24h_lmp(self) -> Dict[int, Dict[str, float]]:
        """
        计算24小时的节点边际电价
        返回: {小时: {节点ID: LMP价格}}
        """
        results = {}
        
        for hour in range(24):
            print(f"正在计算第 {hour} 小时的LMP...")
            
            # 获取该小时的网络状态
            hourly_network = self.day_ahead_data.get_hourly_network(hour)
            
            # 获取该小时的分段报价数据
            hourly_bids = self.day_ahead_data.get_hourly_bid_data(hour)
            
            # 创建LMP算法实例并计算
            lmp_algorithm = LMPAlgorithmWithSegments(hourly_network, hourly_bids)
            lmp_result = lmp_algorithm.calculate_lmp()
            
            results[hour] = lmp_result
        
        self.hourly_results = results
        return results


class LMPAlgorithmWithSegments(LMPAlgorithm):
    """支持分段报价的LMP算法"""
    
    def __init__(self, network: Network, bid_segments: Dict[str, List[BidSegment]] = None):
        super().__init__(network, bid_segments)
        self.bid_segments = bid_segments or {}
    
    def _build_optimization_problem(self) -> Tuple:
        """构建考虑分段报价的优化问题"""
        n_nodes = len(self.network.nodes)
        n_gens = len(self.network.generators)
        
        # 为每台机组的每个报价段创建变量
        gen_list = list(self.network.generators.values())
        segments_info = []  # 存储分段信息
        
        # 计算总的优化变量数量
        total_vars = 0
        for gen in gen_list:
            if gen.id in self.bid_segments and self.bid_segments[gen.id]:
                # 该发电机有分段报价
                segments = self.bid_segments[gen.id]
                segments_info.extend([(gen.id, i, seg) for i, seg in enumerate(segments)])
                total_vars += len(segments)
            else:
                # 该发电机无分段报价（如新能源），使用单一变量
                segments_info.append((gen.id, 0, None))  # None表示无分段
                total_vars += 1
        
        # 目标函数系数（各段的报价）
        c = np.zeros(total_vars)
        
        var_idx = 0
        for gen_id, seg_idx, segment in segments_info:
            if segment is not None:
                # 有分段报价的机组
                c[var_idx] = segment.price
                var_idx += 1
            else:
                # 无分段报价的机组（新能源等）
                gen = self.network.generators[gen_id]
                c[var_idx] = gen.marginal_cost
                var_idx += 1
        
        # 节点功率平衡约束
        A_eq = np.zeros((n_nodes, total_vars))
        b_eq = np.zeros(n_nodes)
        
        # 对每个节点建立功率平衡方程
        var_idx = 0
        for i, gen in enumerate(gen_list):
            if gen.id in self.bid_segments and self.bid_segments[gen.id]:
                # 该发电机有分段报价
                segments = self.bid_segments[gen.id]
                node_idx = self.node_to_idx[gen.node_id]
                
                for j in range(len(segments)):
                    A_eq[node_idx, var_idx + j] = 1.0
                var_idx += len(segments)
            else:
                # 该发电机无分段报价
                node_idx = self.node_to_idx[gen.node_id]
                A_eq[node_idx, var_idx] = 1.0
                var_idx += 1
        
        # 获取该小时的负荷数据
        for node_idx, node_id in self.idx_to_node.items():
            node_loads = self.network.get_loads_at_node(node_id)
            total_load = sum(load.demand for load in node_loads)
            b_eq[node_idx] = total_load  # 负荷作为右端项
        
        # 发电机出力约束（各段容量限制）
        bounds = []
        var_idx = 0
        for gen in gen_list:
            if gen.id in self.bid_segments and self.bid_segments[gen.id]:
                # 有分段报价的机组
                segments = self.bid_segments[gen.id]
                for seg in segments:
                    bounds.append((0, seg.capacity()))
                var_idx += len(segments)
            else:
                # 无分段报价的机组（新能源等）
                bounds.append((gen.min_power, gen.max_power))
                var_idx += 1
        
        # 检查供需平衡
        total_gen_capacity = sum(b[1] for b in bounds if b[1] is not None)  # 上限总和
        total_demand = sum(b_eq)
        
        if total_gen_capacity < total_demand:
            print(f"警告: 总发电容量({total_gen_capacity:.2f}MW)小于总需求({total_demand:.2f}MW)")
        
        return c, A_eq, b_eq, None, None, bounds
    
    def _calculate_simple_lmp(self) -> Dict[str, float]:
        """计算简化的LMP（考虑分段报价）"""
        lmp = {}
        
        for node_id in self.network.nodes.keys():
            # 获取该节点的发电机
            node_gens = [gen for gen in self.network.generators.values() if gen.node_id == node_id]
            
            # 获取该节点的负荷
            node_loads = self.network.get_loads_at_node(node_id)
            total_demand = sum(load.demand for load in node_loads)
            
            if not node_gens:
                lmp[node_id] = 1000.0  # 没有发电机
                continue
            
            # 构建供应曲线
            supply_curve = []
            
            for gen in node_gens:
                if gen.id in self.bid_segments and self.bid_segments[gen.id]:
                    # 该发电机有分段报价
                    segments = self.bid_segments[gen.id]
                    for seg in segments:
                        supply_curve.append((seg.price, seg.capacity()))
                else:
                    # 该发电机无分段报价，使用边际成本
                    capacity = min(gen.max_power, total_demand)  # 简化的容量限制
                    supply_curve.append((gen.marginal_cost, capacity))
            
            # 按价格排序供应曲线
            supply_curve.sort(key=lambda x: x[0])
            
            # 计算满足需求的边际成本
            cumulative_supply = 0.0
            marginal_price = 0.0
            
            for price, capacity in supply_curve:
                cumulative_supply += capacity
                if cumulative_supply >= total_demand:
                    marginal_price = price
                    break
            
            if cumulative_supply < total_demand:
                # 如果供应不足，设定高价格
                marginal_price = max([x[0] for x in supply_curve]) + 500.0 if supply_curve else 800.0
            
            lmp[node_id] = marginal_price
        
        # 考虑网络约束的影响
        self._adjust_lmp_for_network_constraints(lmp)
        
        return lmp


def run_time_series_clearing(day_ahead_data: DayAheadMarketData) -> Dict[int, Dict[str, float]]:
    """
    执行24小时时序现货出清
    :param day_ahead_data: 日前市场数据
    :return: 24小时各节点的边际电价
    """
    algorithm = TimeSeriesLMPAlgorithm(day_ahead_data)
    return algorithm.calculate_24h_lmp()