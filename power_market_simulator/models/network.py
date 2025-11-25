"""
Node structure data model
Define basic elements in power networks such as nodes, generators, loads, etc.
节点结构数据模型
定义电力网络中的节点、发电机、负荷等基本元素
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import numpy as np


class GeneratorType(Enum):
    """Generator type
    发电机类型
    """
    THERMAL = "thermal"  # Thermal power / 火电
    HYDRO = "hydro"      # Hydro power / 水电
    WIND = "wind"        # Wind power / 风电
    SOLAR = "solar"      # Solar power / 光伏


@dataclass
class Node:
    """Power grid node model
    电网节点模型
    """
    id: str
    name: str
    base_voltage: float = 220.0  # Base voltage (kV) / 基准电压(kV)
    x: float = 0.0  # Node coordinate x / 节点坐标x
    y: float = 0.0  # Node coordinate y / 节点坐标y
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class Generator:
    """Generator model
    发电机模型
    """
    id: str
    name: str
    node_id: str
    generator_type: GeneratorType
    min_power: float  # Minimum output (MW) / 最小出力(MW)
    max_power: float  # Maximum output (MW) / 最大出力(MW)
    marginal_cost: float  # Marginal cost (CNY/MWh) / 边际成本(元/MWh)
    startup_cost: float = 0.0  # Startup cost / 启动成本
    shutdown_cost: float = 0.0  # Shutdown cost / 停机成本
    is_online: bool = True  # Whether online / 是否在线
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class Load:
    """Load model
    负荷模型
    """
    id: str
    name: str
    node_id: str
    demand: float  # Load demand (MW) / 负荷需求(MW)
    price_elasticity: float = 0.0  # Price elasticity / 价格弹性
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class TransmissionLine:
    """Transmission line model
    输电线路模型
    """
    id: str
    name: str
    from_node: str  # From node / 起始节点
    to_node: str    # To node / 终止节点
    reactance: float  # Reactance value (p.u.) / 电抗值(p.u.)
    thermal_limit: float  # Thermal limit (MW) / 热稳定极限(MW)
    is_active: bool = True  # Whether active / 是否有效
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class Network:
    """Power grid network structure
    电网网络结构
    """
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
        """Add node
        添加节点
        """
        self.nodes[node.id] = node
    
    def add_generator(self, generator: Generator):
        """Add generator
        添加发电机
        """
        self.generators[generator.id] = generator
    
    def add_load(self, load: Load):
        """Add load
        添加负荷
        """
        self.loads[load.id] = load
    
    def add_line(self, line: TransmissionLine):
        """Add transmission line
        添加输电线路
        """
        self.lines[line.id] = line
    
    def get_generators_at_node(self, node_id: str) -> List[Generator]:
        """Get all generators at specified node
        获取指定节点的所有发电机
        """
        return [gen for gen in self.generators.values() if gen.node_id == node_id]
    
    def get_loads_at_node(self, node_id: str) -> List[Load]:
        """Get all loads at specified node
        获取指定节点的所有负荷
        """
        return [load for load in self.loads.values() if load.node_id == node_id]
    
    def get_connected_nodes(self, node_id: str) -> List[str]:
        """Get nodes connected to the specified node
        获取与指定节点相连的节点
        """
        connected = []
        for line in self.lines.values():
            if line.from_node == node_id and line.is_active:
                connected.append(line.to_node)
            elif line.to_node == node_id and line.is_active:
                connected.append(line.from_node)
        return connected