"""
时间序列和分段报价数据模型
扩展原有的网络模型以支持24小时动态仿真和分段报价
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np
from power_market_simulator.models.network import Network, Generator, Load, GeneratorType


class BidSegment:
    """分段报价段"""
    def __init__(self, start_power: float, end_power: float, price: float):
        self.start_power = start_power  # 段起始出力(MW)
        self.end_power = end_power      # 段结束出力(MW)
        self.price = price              # 该段报价(元/MWh)
    
    def capacity(self) -> float:
        """返回该段容量"""
        return self.end_power - self.start_power


@dataclass
class TimeSlot:
    """时间时段"""
    hour: int  # 小时(0-23)
    load_factor: float = 1.0  # 负荷因子，用于调整基础负荷
    renewable_factor: float = 1.0  # 新能源出力因子，用于调整新能源出力


@dataclass
class GeneratorTimeSeries:
    """发电机时序数据"""
    generator_id: str
    time_slots: List[TimeSlot]  # 24小时数据
    bid_segments: List[List[BidSegment]]  # 每个时段的分段报价，对非新能源机组
    original_generator: Generator  # 原始发电机对象
    
    def get_available_capacity(self, hour: int) -> float:
        """获取指定小时的可用容量"""
        if hour < 0 or hour >= 24:
            raise ValueError("小时必须在0-23之间")
        
        time_slot = self.time_slots[hour]
        
        if self.original_generator.generator_type in [GeneratorType.WIND, GeneratorType.SOLAR]:
            # 新能源机组没有分段报价，出力由可再生能源因子决定
            return self.original_generator.max_power * time_slot.renewable_factor
        else:
            # 传统机组，返回最大出力
            return self.original_generator.max_power
    
    def get_bid_segments(self, hour: int) -> List[BidSegment]:
        """获取指定小时的分段报价"""
        if hour < 0 or hour >= 24:
            raise ValueError("小时必须在0-23之间")
        
        if self.original_generator.generator_type in [GeneratorType.WIND, GeneratorType.SOLAR]:
            # 新能源机组没有分段报价，返回虚拟报价
            capacity = self.get_available_capacity(hour)
            return [BidSegment(0, capacity, 0.0)]  # 新能源报价为0
        else:
            # 传统机组返回实际分段报价
            return self.bid_segments[hour]


@dataclass
class LoadTimeSeries:
    """负荷时序数据"""
    load_id: str
    time_slots: List[TimeSlot]  # 24小时数据
    original_load: Load  # 原始负荷对象
    
    def get_demand(self, hour: int) -> float:
        """获取指定小时的负荷需求"""
        if hour < 0 or hour >= 24:
            raise ValueError("小时必须在0-23之间")
        
        time_slot = self.time_slots[hour]
        return self.original_load.demand * time_slot.load_factor


@dataclass
class DayAheadMarketData:
    """日前市场数据"""
    network: Network  # 基础网络结构
    generator_time_series: Dict[str, GeneratorTimeSeries]  # 发电机时序数据
    load_time_series: Dict[str, LoadTimeSeries]  # 负荷时序数据
    
    def get_hourly_network(self, hour: int) -> Network:
        """获取指定小时的网络状态"""
        # 创建基础网络的副本
        hourly_network = Network(
            name=f"{self.network.name}_H{hour:02d}",
            nodes=self.network.nodes.copy(),
            generators=self.network.generators.copy(),
            loads=self.network.loads.copy(),
            lines=self.network.lines.copy()
        )
        
        # 更新发电机和负荷的时序数据
        for gen_id, gen_ts in self.generator_time_series.items():
            if gen_id in hourly_network.generators:
                original_gen = hourly_network.generators[gen_id]
                new_gen = Generator(
                    id=original_gen.id,
                    name=original_gen.name,
                    node_id=original_gen.node_id,
                    generator_type=original_gen.generator_type,
                    min_power=original_gen.min_power,
                    max_power=gen_ts.get_available_capacity(hour),  # 使用时序容量
                    marginal_cost=original_gen.marginal_cost,
                    startup_cost=original_gen.startup_cost,
                    shutdown_cost=original_gen.shutdown_cost,
                    is_online=original_gen.is_online
                )
                hourly_network.generators[gen_id] = new_gen
        
        # 更新负荷数据
        for load_id, load_ts in self.load_time_series.items():
            if load_id in hourly_network.loads:
                original_load = hourly_network.loads[load_id]
                new_load = Load(
                    id=original_load.id,
                    name=original_load.name,
                    node_id=original_load.node_id,
                    demand=load_ts.get_demand(hour),  # 使用时序负荷
                    price_elasticity=original_load.price_elasticity
                )
                hourly_network.loads[load_id] = new_load
        
        return hourly_network
    
    def get_hourly_bid_data(self, hour: int) -> Dict[str, List[BidSegment]]:
        """获取指定小时的分段报价数据"""
        bid_data = {}
        for gen_id, gen_ts in self.generator_time_series.items():
            bid_data[gen_id] = gen_ts.get_bid_segments(hour)
        return bid_data


def create_sample_day_ahead_data(network: Network) -> DayAheadMarketData:
    """创建示例日前市场数据"""
    generator_time_series = {}
    load_time_series = {}
    
    # 为每个发电机创建24小时时序数据
    for gen_id, gen in network.generators.items():
        # 创建24小时的时隙数据
        time_slots = []
        for h in range(24):
            # 设置负荷因子，模拟日负荷曲线
            if 6 <= h <= 9:  # 早高峰
                load_factor = 0.95
            elif 17 <= h <= 21:  # 晚高峰
                load_factor = 1.0
            elif 22 <= h or h <= 5:  # 夜间低谷
                load_factor = 0.6
            else:  # 平段
                load_factor = 0.8
            
            # 设置新能源出力因子，模拟风光出力曲线
            if gen.generator_type == GeneratorType.WIND:
                # 风电夜间出力较高
                renewable_factor = 0.8 if (22 <= h or h <= 5) else 0.4
            elif gen.generator_type == GeneratorType.SOLAR:
                # 光伏白天出力
                renewable_factor = 0.1 if (h < 7 or h > 19) else max(0.1, 0.2 + 0.7 * (1 - abs(h - 13) / 6))
            else:
                renewable_factor = 1.0  # 传统机组不受影响
            
            time_slots.append(TimeSlot(
                hour=h,
                load_factor=load_factor,
                renewable_factor=renewable_factor
            ))
        
        # 创建分段报价（仅对非新能源机组）
        bid_segments_list = []
        for h in range(24):
            if gen.generator_type in [GeneratorType.WIND, GeneratorType.SOLAR]:
                # 新能源机组无分段报价
                bid_segments_list.append([])
            else:
                # 为传统机组创建分段报价
                # 模拟典型的3段报价
                seg1 = BidSegment(0, gen.max_power * 0.3, gen.marginal_cost)
                seg2 = BidSegment(gen.max_power * 0.3, gen.max_power * 0.7, gen.marginal_cost + 20)
                seg3 = BidSegment(gen.max_power * 0.7, gen.max_power, gen.marginal_cost + 50)
                bid_segments_list.append([seg1, seg2, seg3])
        
        generator_time_series[gen_id] = GeneratorTimeSeries(
            generator_id=gen_id,
            time_slots=time_slots,
            bid_segments=bid_segments_list,
            original_generator=gen
        )
    
    # 为每个负荷创建24小时时序数据
    for load_id, load in network.loads.items():
        time_slots = []
        for h in range(24):
            # 设置负荷因子，模拟日负荷曲线
            if 6 <= h <= 9:  # 早高峰
                load_factor = 0.95
            elif 17 <= h <= 21:  # 晚高峰
                load_factor = 1.0
            elif 22 <= h or h <= 5:  # 夜间低谷
                load_factor = 0.6
            else:  # 平段
                load_factor = 0.8
            
            time_slots.append(TimeSlot(
                hour=h,
                load_factor=load_factor,
                renewable_factor=1.0  # 负荷不受新能源因子影响
            ))
        
        load_time_series[load_id] = LoadTimeSeries(
            load_id=load_id,
            time_slots=time_slots,
            original_load=load
        )
    
    return DayAheadMarketData(
        network=network,
        generator_time_series=generator_time_series,
        load_time_series=load_time_series
    )