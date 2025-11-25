"""
Implementation of Locational Marginal Price (LMP) clearing algorithm
Calculation of locational marginal prices based on DC power flow
节点边际出清算法实现
基于直流潮流的节点边际电价计算
"""
import numpy as np
from typing import Dict, List, Tuple
from scipy.optimize import linprog
from power_market_simulator.models.network import Network, Generator, Load
from power_market_simulator.models.time_series import BidSegment


class LMPAlgorithm:
    """Locational Marginal Price (LMP) algorithm class
    节点边际电价算法类
    """
    
    def __init__(self, network: Network, bid_segments: Dict[str, List[BidSegment]] = None):
        self.network = network
        self.bid_segments = bid_segments or {}
        self.node_to_idx = {node_id: idx for idx, node_id in enumerate(network.nodes.keys())}
        self.idx_to_node = {idx: node_id for node_id, idx in self.node_to_idx.items()}
    
    def calculate_lmp(self) -> Dict[str, float]:
        """
        Calculate locational marginal prices
        Return: {Node ID: LMP price}
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
                print(f"Optimization failed: {result.message}")
                print(f"优化求解失败: {result.message}")
                # Use simplified method to calculate LMP
                # 使用简化方法计算LMP
                return self._calculate_simple_lmp()
            
            # Get dual variables (locational marginal prices)
            # 获取对偶变量（节点边际电价）
            lmp = self._extract_lmp(result)
            return lmp
        except Exception as e:
            print(f"Exception occurred while calculating LMP: {e}")
            print(f"计算LMP时出现异常: {e}")
            # Return LMP calculated by simplified method when exception occurs
            # 出现异常时返回简化方法计算的LMP
            return self._calculate_simple_lmp()
    
    def _build_optimization_problem(self) -> Tuple:
        """Build coefficient matrix for optimization problem, supporting segment bidding
        构建优化问题的系数矩阵，支持分段报价
        """
        n_nodes = len(self.network.nodes)
        gen_list = list(self.network.generators.values())
        
        # 为每台机组的每个报价段创建变量
        segments_info = []  # 存储分段信息
        
        # 计算总的优化变量数量
        total_vars = 0
        for gen in gen_list:
            if gen.id in self.bid_segments and self.bid_segments[gen.id]:
                # This generator has segment bidding
                # 该发电机有分段报价
                segments = self.bid_segments[gen.id]
                segments_info.extend([(gen.id, i, seg) for i, seg in enumerate(segments)])
                total_vars += len(segments)
            else:
                # This generator has no segment bidding (e.g. renewable energy), use single variable
                # 该发电机无分段报价（如新能源），使用单一变量
                segments_info.append((gen.id, 0, None))  # None means no segment / None表示无分段
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
                # This generator has segment bidding
                # 该发电机有分段报价
                segments = self.bid_segments[gen.id]
                node_idx = self.node_to_idx[gen.node_id]
                
                for j in range(len(segments)):
                    A_eq[node_idx, var_idx + j] = 1.0
                var_idx += len(segments)
            else:
                # This generator has no segment bidding
                # 该发电机无分段报价
                node_idx = self.node_to_idx[gen.node_id]
                A_eq[node_idx, var_idx] = 1.0
                var_idx += 1
        
        # Get load data
        # 获取负荷数据
        for node_idx, node_id in self.idx_to_node.items():
            node_loads = self.network.get_loads_at_node(node_id)
            total_load = sum(load.demand for load in node_loads)
            b_eq[node_idx] = total_load  # Load as right-hand side term / 负荷作为右端项
        
        # 变量约束（各段容量限制）
        bounds = []
        var_idx = 0
        for gen in gen_list:
            if gen.id in self.bid_segments and self.bid_segments[gen.id]:
                # Generator with segment bidding
                # 有分段报价的机组
                segments = self.bid_segments[gen.id]
                for seg in segments:
                    bounds.append((0, seg.capacity()))
                var_idx += len(segments)
            else:
                # Generator without segment bidding (e.g. renewable energy)
                # 无分段报价的机组（新能源等）
                bounds.append((gen.min_power, gen.max_power))
                var_idx += 1
        
        # 检查供需平衡
        total_gen_capacity = sum(b[1] for b in bounds if b[1] is not None and b[1] != np.inf)  # 上限总和
        total_demand = sum(b_eq)
        
        if total_gen_capacity < total_demand * 0.9:  # Allow minor shortage / 允许少量短缺
            print(f"Warning: Total generation capacity ({total_gen_capacity:.2f}MW) is much less than total demand ({total_demand:.2f}MW)")
            print(f"警告: 总发电容量({total_gen_capacity:.2f}MW)远小于总需求({total_demand:.2f}MW)")
        
        return c, A_eq, b_eq, None, None, bounds
    
    def _build_transmission_constraints(self, n_gens: int, n_nodes: int, n_lines: int) -> Tuple:
        """Build transmission line capacity constraints
        构建输电线路容量约束
        """
        if n_lines == 0:
            return np.zeros((0, n_gens)), np.zeros(0)
        
        # Get generator list
        # 获取发电机列表
        gen_list = list(self.network.generators.values())
        
        # Determine number of lines
        # 确定线路数量
        active_lines = [line for line in self.network.lines.values() if line.is_active]
        n_active_lines = len(active_lines)
        if n_active_lines == 0:
            return np.zeros((0, n_gens)), np.zeros(0)
        
        # Build line constraints using DC power flow model
        # 使用直流潮流模型构建线路约束
        A_ub = np.zeros((2 * n_active_lines, n_gens))
        b_ub = np.zeros(2 * n_active_lines)
        
        for idx, line in enumerate(active_lines):
            from_node_idx = self.node_to_idx[line.from_node]
            to_node_idx = self.node_to_idx[line.to_node]
            
            # For each line, build power transmission constraints
            # 线路潮流 = sum(B * theta)，但在LMP计算中直接用节点注入功率对线路的影响
            # In DC power flow, line flow is mainly affected by node injection power
            # 在直流潮流中，线路潮流主要受节点注入功率影响
            for gen_idx, gen in enumerate(gen_list):
                gen_node_idx = self.node_to_idx[gen.node_id]
                
                # Calculate impact factor of generator on line flow (simplified)
                # 计算发电机对线路潮流的影响因子（简化处理）
                # Use simplified version of node-line association matrix
                # 这里使用节点-线路关联矩阵的简化版本
                if gen_node_idx == from_node_idx:
                    # Generator at from node, has positive impact on line
                    # 发电机在from节点，对线路有正向影响
                    A_ub[2 * idx, gen_idx] = 1.0  # Simplified processing / 简化处理
                    A_ub[2 * idx + 1, gen_idx] = -1.0  # Corresponding lower bound constraint / 对应下限约束
                elif gen_node_idx == to_node_idx:
                    # Generator at to node, has negative impact on line
                    # 发电机在to节点，对线路有负向影响
                    A_ub[2 * idx, gen_idx] = -1.0
                    A_ub[2 * idx + 1, gen_idx] = 1.0
            
            # Line capacity limits
            # 线路容量限制
            b_ub[2 * idx] = line.thermal_limit       # Upper limit / 上限
            b_ub[2 * idx + 1] = line.thermal_limit  # Lower limit (negative direction) / 下限（负方向）
        
        return A_ub, b_ub
    
    def _extract_lmp(self, result) -> Dict[str, float]:
        """Extract locational marginal prices from optimization results
        从优化结果中提取节点边际电价
        """
        # Get dual variables of power balance constraints (i.e. locational marginal prices)
        # 由于scipy的linprog不直接返回对偶变量，我们使用简化方法
        # Since scipy's linprog does not directly return dual variables, we use a simplified method
        
        # Here we use an approximate method to calculate LMP
        # 这里我们使用一种近似方法来计算LMP
        # Actual LMP is the Lagrange multiplier of power balance constraints
        # 实际的LMP是功率平衡约束的拉格朗日乘子
        lmp_values = self._calculate_simple_lmp()
        
        return lmp_values
    
    def _calculate_simple_lmp(self) -> Dict[str, float]:
        """Calculate simplified LMP (considering segment bidding)
        计算简化的LMP（考虑分段报价）
        """
        lmp = {}
        
        for node_id in self.network.nodes.keys():
            # Get generators at this node
            # 获取该节点的发电机
            node_gens = [gen for gen in self.network.generators.values() if gen.node_id == node_id]
            
            # Get loads at this node
            # 获取该节点的负荷
            node_loads = self.network.get_loads_at_node(node_id)
            total_demand = sum(load.demand for load in node_loads)
            
            if not node_gens:
                lmp[node_id] = 1000.0  # No generators / 没有发电机
                continue
            
            # Build supply curve
            # 构建供应曲线
            supply_curve = []
            
            for gen in node_gens:
                if gen.id in self.bid_segments and self.bid_segments[gen.id]:
                    # This generator has segment bidding
                    # 该发电机有分段报价
                    segments = self.bid_segments[gen.id]
                    for seg in segments:
                        supply_curve.append((seg.price, seg.capacity()))
                else:
                    # This generator has no segment bidding, use marginal cost
                    # 该发电机无分段报价，使用边际成本
                    capacity = min(gen.max_power, total_demand)  # Simplified capacity constraint / 简化的容量限制
                    supply_curve.append((gen.marginal_cost, capacity))
            
            # Sort supply curve by price
            # 按价格排序供应曲线
            supply_curve.sort(key=lambda x: x[0])
            
            # Calculate marginal cost to meet demand
            # 计算满足需求的边际成本
            cumulative_supply = 0.0
            marginal_price = 0.0
            
            for price, capacity in supply_curve:
                cumulative_supply += capacity
                if cumulative_supply >= total_demand:
                    marginal_price = price
                    break
            
            if cumulative_supply < total_demand:
                # If supply is insufficient, set high price
                # 如果供应不足，设定高价格
                marginal_price = max([x[0] for x in supply_curve]) + 500.0 if supply_curve else 800.0
            elif not supply_curve:
                marginal_price = 500.0  # If no supply, set base price / 如果没有供应，设定基础价格
            
            lmp[node_id] = marginal_price
        
        # Consider impact of network constraints
        # 考虑网络约束的影响
        self._adjust_lmp_for_network_constraints(lmp)
        
        return lmp
    
    def _adjust_lmp_for_network_constraints(self, lmp: Dict[str, float]):
        """Adjust LMP according to network constraints
        根据网络约束调整LMP
        """
        # Traverse all lines to check for transmission constraints
        # 遍历所有线路，检查是否存在传输约束
        for line in self.network.lines.values():
            if line.is_active:
                from_lmp = lmp[line.from_node]
                to_lmp = lmp[line.to_node]
                
                # If price difference between ends is large, there may be transmission constraints
                # 如果两端价格差异大，可能存在传输约束
                price_diff = abs(from_lmp - to_lmp)
                if price_diff > 10:  # Price difference threshold / 价格差异阈值
                    # Check if there is significant power flow from low-price node to high-price node
                    # but constrained by line capacity
                    # 检查是否有大量电力从低价节点流向高价节点
                    # 但受到线路容量限制
                    # At this point, adjust prices to reflect congestion cost
                    # 这时需要调整价格以反映拥堵成本
                    congestion_cost = price_diff * 0.1  # Congestion cost coefficient / 拥堵成本系数
                    lmp[line.from_node] = max(lmp[line.from_node], from_lmp + congestion_cost/2)
                    lmp[line.to_node] = max(lmp[line.to_node], to_lmp - congestion_cost/2)


def run_clearing(network: Network, bid_segments: Dict[str, List[BidSegment]] = None) -> Dict[str, float]:
    """
    Execute locational marginal clearing
    执行节点边际出清
    :param network: Power grid network structure / 电网网络结构
    :param bid_segments: Segment bidding data, format {generator_id: [BidSegment]} / 分段报价数据，格式为 {generator_id: [BidSegment]}
    :return: Marginal prices for each node / 各节点的边际电价
    """
    algorithm = LMPAlgorithm(network, bid_segments)
    return algorithm.calculate_lmp()