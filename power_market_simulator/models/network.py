"""
节点结构数据模型
定义电力网络中的节点、发电机、负荷等基本元素
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import numpy as np


class GeneratorType(Enum):
    """发电机类型"""
    THERMAL = "thermal"  # 火电
    HYDRO = "hydro"      # 水电
    WIND = "wind"        # 风电
    SOLAR = "solar"      # 光伏


@dataclass
class Node:
    """电网节点模型"""
    id: str
    name: str
    base_voltage: float = 220.0  # 基准电压(kV)
    x: float = 0.0  # 节点坐标x
    y: float = 0.0  # 节点坐标y
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class Generator:
    """发电机模型"""
    id: str
    name: str
    node_id: str
    generator_type: GeneratorType
    min_power: float  # 最小出力(MW)
    max_power: float  # 最大出力(MW)
    marginal_cost: float  # 边际成本(元/MWh)
    startup_cost: float = 0.0  # 启动成本
    shutdown_cost: float = 0.0  # 停机成本
    is_online: bool = True  # 是否在线
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class Load:
    """负荷模型"""
    id: str
    name: str
    node_id: str
    demand: float  # 负荷需求(MW)
    price_elasticity: float = 0.0  # 价格弹性
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class TransmissionLine:
    """输电线路模型"""
    id: str
    name: str
    from_node: str  # 起始节点
    to_node: str    # 终止节点
    reactance: float  # 电抗值(p.u.)
    thermal_limit: float  # 热稳定极限(MW)
    is_active: bool = True  # 是否有效
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class Network:
    """电网网络结构"""
    name: str
    nodes: Dict[str, Node] = None
    generators: Dict[str, Generator] = None
    loads: Dict[str, Load] = None
    lines: Dict[str, TransmissionLine] = None
    
    def __post_init__(self):
        if self.nodes is None:
            self.nodes = {}
        if self.generators is None:
            self.generators = {}
        if self.loads is None:
            self.loads = {}
        if self.lines is None:
            self.lines = {}
    
    def add_node(self, node: Node):
        """添加节点"""
        self.nodes[node.id] = node
    
    def add_generator(self, generator: Generator):
        """添加发电机"""
        self.generators[generator.id] = generator
    
    def add_load(self, load: Load):
        """添加负荷"""
        self.loads[load.id] = load
    
    def add_line(self, line: TransmissionLine):
        """添加输电线路"""
        self.lines[line.id] = line
    
    def get_generators_at_node(self, node_id: str) -> List[Generator]:
        """获取指定节点的所有发电机"""
        return [gen for gen in self.generators.values() if gen.node_id == node_id]
    
    def get_loads_at_node(self, node_id: str) -> List[Load]:
        """获取指定节点的所有负荷"""
        return [load for load in self.loads.values() if load.node_id == node_id]
    
    def get_connected_nodes(self, node_id: str) -> List[str]:
        """获取与指定节点相连的节点"""
        connected = []
        for line in self.lines.values():
            if line.from_node == node_id and line.is_active:
                connected.append(line.to_node)
            elif line.to_node == node_id and line.is_active:
                connected.append(line.from_node)
        return connected