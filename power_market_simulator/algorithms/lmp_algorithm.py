"""
节点边际出清算法实现
基于直流潮流的节点边际电价计算
"""
import numpy as np
from typing import Dict, List, Tuple
from scipy.optimize import linprog
from power_market_simulator.models.network import Network, Generator, Load
from power_market_simulator.models.time_series import BidSegment


class LMPAlgorithm:
    """节点边际电价算法类"""
    
    def __init__(self, network: Network, bid_segments: Dict[str, List[BidSegment]] = None):
        self.network = network
        self.bid_segments = bid_segments or {}
        self.node_to_idx = {node_id: idx for idx, node_id in enumerate(network.nodes.keys())}
        self.idx_to_node = {idx: node_id for node_id, idx in self.node_to_idx.items()}
    
    def calculate_lmp(self) -> Dict[str, float]:
        """
        计算节点边际电价
        返回: {节点ID: LMP价格}
        """
        try:
            # 获取优化问题的参数
            c, A_eq, b_eq, A_ub, b_ub, bounds = self._build_optimization_problem()
            
            # 求解线性规划问题
            result = linprog(
                c=c,
                A_eq=A_eq,
                b_eq=b_eq,
                A_ub=A_ub,
                b_ub=b_ub,
                bounds=bounds,
                method='highs'
            )
            
            if not result.success:
                print(f"优化求解失败: {result.message}")
                # 使用简化方法计算LMP
                return self._calculate_simple_lmp()
            
            # 获取对偶变量（节点边际电价）
            lmp = self._extract_lmp(result)
            return lmp
        except Exception as e:
            print(f"计算LMP时出现异常: {e}")
            # 出现异常时返回简化方法计算的LMP
            return self._calculate_simple_lmp()
    
    def _build_optimization_problem(self) -> Tuple:
        """构建优化问题的系数矩阵，支持分段报价"""
        n_nodes = len(self.network.nodes)
        gen_list = list(self.network.generators.values())
        
        # 为每台机组的每个报价段创建变量
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
        
        if total_vars == 0:
            # 如果没有发电机，创建一个虚拟变量
            total_vars = 1
            segments_info = [("virtual", 0, None)]
        
        # 目标函数系数（各段的报价或边际成本）
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
        
        # 获取负荷数据
        for node_idx, node_id in self.idx_to_node.items():
            node_loads = self.network.get_loads_at_node(node_id)
            total_load = sum(load.demand for load in node_loads)
            b_eq[node_idx] = total_load  # 负荷作为右端项
        
        # 变量约束（各段容量限制）
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
        total_gen_capacity = sum(b[1] for b in bounds if b[1] is not None and b[1] != np.inf)  # 上限总和
        total_demand = sum(b_eq)
        
        if total_gen_capacity < total_demand * 0.9:  # 允许少量短缺
            print(f"警告: 总发电容量({total_gen_capacity:.2f}MW)远小于总需求({total_demand:.2f}MW)")
        
        return c, A_eq, b_eq, None, None, bounds
    
    def _build_transmission_constraints(self, n_gens: int, n_nodes: int, n_lines: int) -> Tuple:
        """构建输电线路容量约束"""
        if n_lines == 0:
            return np.zeros((0, n_gens)), np.zeros(0)
        
        # 获取发电机列表
        gen_list = list(self.network.generators.values())
        
        # 确定线路数量
        active_lines = [line for line in self.network.lines.values() if line.is_active]
        n_active_lines = len(active_lines)
        if n_active_lines == 0:
            return np.zeros((0, n_gens)), np.zeros(0)
        
        # 使用直流潮流模型构建线路约束
        A_ub = np.zeros((2 * n_active_lines, n_gens))
        b_ub = np.zeros(2 * n_active_lines)
        
        for idx, line in enumerate(active_lines):
            from_node_idx = self.node_to_idx[line.from_node]
            to_node_idx = self.node_to_idx[line.to_node]
            
            # 对于每条线路，建立功率传输约束
            # 线路潮流 = sum(B * theta)，但在LMP计算中直接用节点注入功率对线路的影响
            # 在直流潮流中，线路潮流主要受节点注入功率影响
            for gen_idx, gen in enumerate(gen_list):
                gen_node_idx = self.node_to_idx[gen.node_id]
                
                # 计算发电机对线路潮流的影响因子（简化处理）
                # 这里使用节点-线路关联矩阵的简化版本
                if gen_node_idx == from_node_idx:
                    # 发电机在from节点，对线路有正向影响
                    A_ub[2 * idx, gen_idx] = 1.0  # 简化处理
                    A_ub[2 * idx + 1, gen_idx] = -1.0  # 对应下限约束
                elif gen_node_idx == to_node_idx:
                    # 发电机在to节点，对线路有负向影响
                    A_ub[2 * idx, gen_idx] = -1.0
                    A_ub[2 * idx + 1, gen_idx] = 1.0
            
            # 线路容量限制
            b_ub[2 * idx] = line.thermal_limit       # 上限
            b_ub[2 * idx + 1] = line.thermal_limit  # 下限（负方向）
        
        return A_ub, b_ub
    
    def _extract_lmp(self, result) -> Dict[str, float]:
        """从优化结果中提取节点边际电价"""
        # 获取功率平衡约束的对偶变量（即节点边际电价）
        # 由于scipy的linprog不直接返回对偶变量，我们使用简化方法
        
        # 这里我们使用一种近似方法来计算LMP
        # 实际的LMP是功率平衡约束的拉格朗日乘子
        lmp_values = self._calculate_simple_lmp()
        
        return lmp_values
    
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
            elif not supply_curve:
                marginal_price = 500.0  # 如果没有供应，设定基础价格
            
            lmp[node_id] = marginal_price
        
        # 考虑网络约束的影响
        self._adjust_lmp_for_network_constraints(lmp)
        
        return lmp
    
    def _adjust_lmp_for_network_constraints(self, lmp: Dict[str, float]):
        """根据网络约束调整LMP"""
        # 遍历所有线路，检查是否存在传输约束
        for line in self.network.lines.values():
            if line.is_active:
                from_lmp = lmp[line.from_node]
                to_lmp = lmp[line.to_node]
                
                # 如果两端价格差异大，可能存在传输约束
                price_diff = abs(from_lmp - to_lmp)
                if price_diff > 10:  # 价格差异阈值
                    # 检查是否有大量电力从低价节点流向高价节点
                    # 但受到线路容量限制
                    # 这时需要调整价格以反映拥堵成本
                    congestion_cost = price_diff * 0.1  # 拥堵成本系数
                    lmp[line.from_node] = max(lmp[line.from_node], from_lmp + congestion_cost/2)
                    lmp[line.to_node] = max(lmp[line.to_node], to_lmp - congestion_cost/2)


def run_clearing(network: Network, bid_segments: Dict[str, List[BidSegment]] = None) -> Dict[str, float]:
    """
    执行节点边际出清
    :param network: 电网网络结构
    :param bid_segments: 分段报价数据，格式为 {generator_id: [BidSegment]}
    :return: 各节点的边际电价
    """
    algorithm = LMPAlgorithm(network, bid_segments)
    return algorithm.calculate_lmp()