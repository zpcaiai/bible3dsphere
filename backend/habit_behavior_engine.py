"""
人格塑造、习惯养成、行为追踪系统 - 完整引擎实现
从 emotion-sphere 项目移植

L0-L4 架构：
- L0: 行为调节引擎 (Behavior Regulation Engine)
- L1: 习惯状态机引擎 (Habit State Machine Engine)  
- L2: 执行力边缘引导引擎 (Execution Edge Intervention Engine)
- L3: 微调度器引擎 (Micro Scheduler Engine)
- L4: 身份认同强化引擎 (Identity Reinforcement Engine)

理论基础:
- B.J. Fogg 福格行为模型: B = MAP (行为=动机×能力×触发)
- 三层动态电路保护: Green/Yellow/Red Tier
- 代币激励系统: 游戏化信用账本
"""

import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional, List, Dict

# LLM调用函数占位符 - 需要在main.py中实现
call_chat = None


def set_call_chat_fn(fn):
    """设置LLM调用函数"""
    global call_chat
    call_chat = fn


# ============================================================
# 数据类定义 (Data Classes)
# ============================================================

@dataclass
class BehaviorRegulationResult:
    """行为调节结果"""
    current_resistance: int = 5
    current_psychological_state: str = ""
    min_executable_action: str = ""
    task_downgrade: str = ""
    emotional_compensation: str = ""
    continuity_advice: str = ""
    selected_tier: str = "Yellow"
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HabitStateMachineResult:
    """习惯状态机执行结果"""
    habit_name: str = ""
    deterministic_anchor: str = ""
    selected_tier: str = "Yellow"
    action_to_execute: str = ""
    token_yield: int = 5
    anti_guilt_message: str = ""
    energy_level: int = 3
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IgnitionStep:
    """点火序列步骤"""
    step_order: int
    action_description: str
    estimated_seconds: int
    psychological_nudge: str
    completion_criteria: str
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExecutionEdgeInterventionResult:
    """执行力边缘引导结果"""
    paralysis_type: str = ""
    detected_signals: List[Dict] = field(default_factory=list)
    ignition_sequence: List[IgnitionStep] = field(default_factory=list)
    micro_momentum_score: int = 0
    total_estimated_seconds: int = 120
    hardware_context_isolation: Dict = field(default_factory=dict)
    emotional_stabilization: str = ""
    
    def to_dict(self) -> dict:
        return {
            "paralysis_type": self.paralysis_type,
            "detected_signals": self.detected_signals,
            "ignition_sequence": [s.to_dict() for s in self.ignition_sequence],
            "micro_momentum_score": self.micro_momentum_score,
            "total_estimated_seconds": self.total_estimated_seconds,
            "hardware_context_isolation": self.hardware_context_isolation,
            "emotional_stabilization": self.emotional_stabilization
        }


@dataclass
class DecoupledStep:
    """解耦步骤"""
    step_id: str
    action: str
    duration_seconds: int
    completed: bool = False


@dataclass
class MicroSchedulerResult:
    """微调度器结果"""
    session_id: str = ""
    original_task: str = ""
    decoupled_chain: List[DecoupledStep] = field(default_factory=list)
    current_step_index: int = 0
    noise_floor_level: int = 5
    context_isolation_config: Dict = field(default_factory=dict)
    momentum_score: int = 0
    completed_steps: int = 0
    total_steps: int = 0
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "original_task": self.original_task,
            "decoupled_chain": [asdict(s) for s in self.decoupled_chain],
            "current_step_index": self.current_step_index,
            "noise_floor_level": self.noise_floor_level,
            "context_isolation_config": self.context_isolation_config,
            "momentum_score": self.momentum_score,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps
        }


@dataclass
class IdentityReinforcementResult:
    """身份认同强化结果"""
    current_narrative: str = ""
    narrative_type: str = "stable"
    negative_identity_labels: List[str] = field(default_factory=list)
    target_identity: str = ""
    reinforcement_language: str = ""
    long_term_migration: str = ""
    migration_progress: int = 50
    
    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# L0: 行为调节引擎 (Behavior Regulation Engine)
# ============================================================

class BehaviorRegulationEngine:
    """
    行为调节引擎 (L0)
    核心原则：行为启动 > 行为完成，避免羞耻感，降低认知负担
    """
    
    SYSTEM_PROMPT = """你是"行为工程调节系统"。

核心原则：
- 行为启动 > 行为完成
- 避免羞耻感
- 降低认知负担
- 小步持续优于短期爆发
- 用户失败时优先保护心理连续性

目标：不是让用户"完美完成"，而是让用户"不退出系统"。

输出严格JSON格式：
{
  "current_resistance": 1-10,
  "current_psychological_state": "状态描述",
  "min_executable_action": "30秒内可启动的最小动作",
  "task_downgrade": "降级版本的任务",
  "emotional_compensation": "如果未完成，如何保护心理连续性",
  "continuity_advice": "维持行为连续性的具体建议",
  "selected_tier": "Green/Yellow/Red"
}"""

    def regulate(self, target_task: str, energy_level: int = 3,
                 motivation: int = 5, previous_failures: int = 0) -> BehaviorRegulationResult:
        """动态调节行为执行策略"""
        context = f"目标: {target_task}\n能量: {energy_level}/5\n动机: {motivation}/10\n失败: {previous_failures}次"
        
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT, context, temperature=0.4)
            else:
                raw = self._mock_regulation(energy_level)
            
            data = self._parse_json(raw)
            return BehaviorRegulationResult(
                current_resistance=data.get("current_resistance", 5),
                current_psychological_state=data.get("current_psychological_state", ""),
                min_executable_action=data.get("min_executable_action", "深呼吸三次"),
                task_downgrade=data.get("task_downgrade", target_task),
                emotional_compensation=data.get("emotional_compensation", ""),
                continuity_advice=data.get("continuity_advice", ""),
                selected_tier=data.get("selected_tier", self._tier_from_energy(energy_level))
            )
        except Exception as e:
            print(f"[BehaviorRegulation] Failed: {e}", flush=True)
            return self._fallback_regulation(target_task, energy_level)
    
    def _tier_from_energy(self, energy: int) -> str:
        if energy >= 4: return "Green"
        elif energy >= 3: return "Yellow"
        return "Red"
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except Exception:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try: return json.loads(m.strip())
                    except: continue
        return {}
    
    def _fallback_regulation(self, task: str, energy: int) -> BehaviorRegulationResult:
        if energy <= 2:
            return BehaviorRegulationResult(
                current_resistance=8,
                current_psychological_state="低能量，高阻力",
                min_executable_action=f"打开'{task}'相关文档，读第一行",
                task_downgrade=f"{task}最小版本（60秒）",
                emotional_compensation="系统已切换到低能耗模式，这不是失败",
                continuity_advice="任何微小启动都算作成功",
                selected_tier="Red"
            )
        elif energy <= 3:
            return BehaviorRegulationResult(
                current_resistance=5,
                current_psychological_state="正常能量，中等阻力",
                min_executable_action=f"开始'{task}'第一步，限时5分钟",
                task_downgrade=f"{task}简化版（5分钟）",
                emotional_compensation="完成50%也算成功",
                continuity_advice="设定番茄钟，专注一小段时间",
                selected_tier="Yellow"
            )
        return BehaviorRegulationResult(
            current_resistance=3,
            current_psychological_state="高能量，低阻力",
            min_executable_action=f"完整执行'{task}'",
            task_downgrade=task,
            emotional_compensation="保持节奏，但不要过度消耗",
            continuity_advice="记录这次成功的感觉",
            selected_tier="Green"
        )
    
    def _mock_regulation(self, energy: int) -> str:
        tier = self._tier_from_energy(energy)
        actions = {
            "Green": ("完整任务执行", "完整版本", "保持节奏"),
            "Yellow": ("任务简化版（5分钟）", "启动第一步", "完成部分也是成功"),
            "Red": ("60秒原子动作", "打开文档读一行", "系统智能降级")
        }
        action, downgrade, compensation = actions.get(tier, actions["Yellow"])
        return json.dumps({
            "current_resistance": 8 if tier == "Red" else (5 if tier == "Yellow" else 3),
            "current_psychological_state": "低能量" if tier == "Red" else ("正常" if tier == "Yellow" else "高能量"),
            "min_executable_action": action,
            "task_downgrade": downgrade,
            "emotional_compensation": compensation,
            "continuity_advice": "任何启动都算成功" if tier == "Red" else "保持节奏",
            "selected_tier": tier
        })


# ============================================================
# L1: 习惯状态机引擎 (Habit State Machine Engine)
# ============================================================

class HabitStateMachineEngine:
    """
    习惯状态机引擎 (L1)
    基于福格行为模型 B=MAP，三层动态电路保护
    """
    
    SYSTEM_PROMPT = """你是"习惯状态机架构师"。

基于福格行为模型 B=MAP，设计三层动态习惯状态机。

输出严格JSON：
{
  "deterministic_anchor": "硬编码锚点（不可跳过的日常动作）",
  "tier_configs": {
    "green": {"action_script": "完整习惯（能量4-5）", "estimated_duration": 分钟数, "token_yield": 10},
    "yellow": {"action_script": "标准版本（能量3）", "estimated_duration": 分钟数, "token_yield": 5},
    "red": {"action_script": "60秒原子动作（能量1-2）", "estimated_duration": 1, "token_yield": 1}
  },
  "anti_guilt_message": "低能量时的系统状态通知"
}"""

    def create_habit_fsm(self, habit_name: str, existing_anchor: str = "") -> dict:
        """创建新的习惯状态机"""
        context = f"目标习惯: {habit_name}\n锚点: {existing_anchor}"
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT, context, temperature=0.5)
            else:
                raw = self._mock_fsm(habit_name)
            return self._parse_json(raw)
        except Exception as e:
            print(f"[HabitFSM] Creation failed: {e}", flush=True)
            return self._fallback_fsm(habit_name)
    
    def execute_habit(self, habit_config: dict, current_energy: int = 3) -> HabitStateMachineResult:
        """根据当前能量执行习惯状态机"""
        tier = self._select_tier(current_energy)
        tier_config = habit_config.get("tier_configs", {}).get(tier.lower(), {})
        
        anti_guilt = ""
        if current_energy <= 2:
            anti_guilt = "系统状态：高负荷。执行已路由至Red Tier。连胜保持。核心控制回路完整性：100%。"
        
        return HabitStateMachineResult(
            habit_name=habit_config.get("habit_name", "未命名"),
            deterministic_anchor=habit_config.get("deterministic_anchor", ""),
            selected_tier=tier,
            action_to_execute=tier_config.get("action_script", "深呼吸三次"),
            token_yield=tier_config.get("token_yield", 1),
            anti_guilt_message=anti_guilt,
            energy_level=current_energy
        )
    
    def _select_tier(self, energy: int) -> str:
        if energy >= 4: return "Green"
        elif energy >= 3: return "Yellow"
        return "Red"
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except Exception:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try: return json.loads(m.strip())
                    except: continue
        return {}
    
    def _fallback_fsm(self, habit_name: str) -> dict:
        return {
            "habit_name": habit_name,
            "deterministic_anchor": "早晨刷牙后",
            "tier_configs": {
                "green": {"action_script": f"完整{habit_name}（15分钟）", "estimated_duration": 15, "token_yield": 10},
                "yellow": {"action_script": f"简化{habit_name}（5分钟）", "estimated_duration": 5, "token_yield": 5},
                "red": {"action_script": f"原子版{habit_name}：只做第一步（60秒）", "estimated_duration": 1, "token_yield": 1}
            },
            "anti_guilt_message": "系统已切换至保护模式，连胜保持。"
        }
    
    def _mock_fsm(self, habit_name: str) -> str:
        return json.dumps({
            "habit_name": habit_name,
            "deterministic_anchor": "倒第一杯咖啡后",
            "tier_configs": {
                "green": {"action_script": f"完整{habit_name}", "estimated_duration": 20, "token_yield": 10},
                "yellow": {"action_script": f"标准{habit_name}", "estimated_duration": 10, "token_yield": 5},
                "red": {"action_script": f"打开{habit_name}看一眼", "estimated_duration": 1, "token_yield": 1}
            },
            "anti_guilt_message": "系统状态：高负荷。执行已路由至Red Tier。连胜保持。"
        })


# ============================================================
# 习惯系统协调器 (Habit Coordinator)
# ============================================================

class HabitCoordinator:
    """习惯系统协调器"""
    
    def __init__(self):
        self.regulation_engine = BehaviorRegulationEngine()
        self.fsm_engine = HabitStateMachineEngine()
    
    def create_and_execute(self, habit_name: str, energy_level: int = 3, 
                          existing_anchor: str = "") -> dict:
        """创建习惯并获取执行计划"""
        fsm_config = self.fsm_engine.create_habit_fsm(habit_name, existing_anchor)
        fsm_config["habit_name"] = habit_name
        execution = self.fsm_engine.execute_habit(fsm_config, energy_level)
        regulation = self.regulation_engine.regulate(habit_name, energy_level, energy_level * 2)
        return {
            "habit_config": fsm_config,
            "execution_plan": execution.to_dict(),
            "regulation": regulation.to_dict()
        }


# ============================================================
# L2: 执行力边缘引导引擎 (Execution Edge Intervention)
# ============================================================

class ExecutionEdgeInterventionEngine:
    """
    执行力边缘引导引擎 (L2)
    在用户即将放弃时进行实时微干预
    """
    
    SYSTEM_PROMPT = """你是"执行力边缘引导系统"。

用户处于"即将放弃"的执行边缘，提供2分钟"点火序列"。

输出JSON格式：
{
  "paralysis_type": "distraction/procrastination/anxiety_avoidance/emotional_collapse",
  "detected_signals": [{"signal_type": "", "description": "", "intensity": 8}],
  "ignition_sequence": [{"step_order": 1, "action_description": "", "estimated_seconds": 30, "psychological_nudge": "", "completion_criteria": ""}],
  "micro_momentum_score": 75,
  "hardware_context_isolation": {"hide_tabs": [], "mute_notifications": true, "focus_window": ""},
  "emotional_stabilization": ""
}

设计原则：每个步骤30秒内可完成，逐步提升心理动能，防羞耻语言。"""

    def intervene(self, raw_backlog_task: str, detected_signals: List[Dict],
                  edge_context: Dict, previous_interventions: int = 0) -> ExecutionEdgeInterventionResult:
        """执行力崩溃干预"""
        context = f"任务: {raw_backlog_task}\n信号: {json.dumps(detected_signals)}\n干预次数: {previous_interventions}"
        
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT, context, temperature=0.4)
            else:
                raw = self._mock_intervention(raw_backlog_task)
            
            data = self._parse_json(raw)
            ignition_steps = [IgnitionStep(
                step_order=s.get("step_order", 1),
                action_description=s.get("action_description", ""),
                estimated_seconds=s.get("estimated_seconds", 30),
                psychological_nudge=s.get("psychological_nudge", ""),
                completion_criteria=s.get("completion_criteria", "")
            ) for s in data.get("ignition_sequence", [])]
            
            return ExecutionEdgeInterventionResult(
                paralysis_type=data.get("paralysis_type", "distraction"),
                detected_signals=data.get("detected_signals", detected_signals),
                ignition_sequence=ignition_steps,
                micro_momentum_score=data.get("micro_momentum_score", 50),
                total_estimated_seconds=sum(s.estimated_seconds for s in ignition_steps),
                hardware_context_isolation=data.get("hardware_context_isolation", {}),
                emotional_stabilization=data.get("emotional_stabilization", "")
            )
        except Exception as e:
            print(f"[EdgeIntervention] Failed: {e}", flush=True)
            return self._fallback_intervention(raw_backlog_task)
    
    def detect_paralysis_signals(self, tab_switch_count: int, idle_duration_seconds: int,
                                  window_thrashing: bool, current_task: str) -> List[Dict]:
        """检测执行力崩溃信号"""
        signals = []
        if tab_switch_count > 10:
            signals.append({"signal_type": "高频切换", "description": f"3分钟切换{tab_switch_count}次", "intensity": min(tab_switch_count/3, 10)})
        if idle_duration_seconds > 180:
            signals.append({"signal_type": "无意义浏览", "description": f"无目标浏览{idle_duration_seconds//60}分钟", "intensity": min(idle_duration_seconds/60, 10)})
        if window_thrashing:
            signals.append({"signal_type": "系统抖动", "description": "窗口频繁切换", "intensity": 8})
        return signals
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except Exception:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try: return json.loads(m.strip())
                    except: continue
        return {}
    
    def _fallback_intervention(self, task: str) -> ExecutionEdgeInterventionResult:
        steps = [
            IgnitionStep(1, "深呼吸3次", 20, "让身体放松", "完成3次深呼吸"),
            IgnitionStep(2, f"打开{task}窗口", 30, "只是打开", "窗口已打开"),
            IgnitionStep(3, f"看{task}第一行", 40, "只是看一眼", "视线已接触"),
            IgnitionStep(4, f"写第一个想法", 30, "不需要完整", "有文字出现")
        ]
        return ExecutionEdgeInterventionResult(
            paralysis_type="distraction",
            detected_signals=[{"signal_type": "系统默认", "description": "降级干预", "intensity": 5}],
            ignition_sequence=steps,
            micro_momentum_score=50,
            total_estimated_seconds=120,
            hardware_context_isolation={"hide_tabs": ["无关"], "mute_notifications": True, "focus_window": "当前任务"},
            emotional_stabilization="检测到你可能有些分心。这不是失败，只是需要调整。"
        )
    
    def _mock_intervention(self, task: str) -> str:
        return json.dumps({
            "paralysis_type": "distraction",
            "detected_signals": [{"signal_type": "高频切换", "description": "3分钟切换12次", "intensity": 8}],
            "ignition_sequence": [
                {"step_order": 1, "action_description": "关闭无关标签", "estimated_seconds": 20, "psychological_nudge": "环境清理", "completion_criteria": "只剩必要标签"},
                {"step_order": 2, "action_description": f"看一眼{task}", "estimated_seconds": 10, "psychological_nudge": "不承诺行动", "completion_criteria": "视线接触"},
                {"step_order": 3, "action_description": f"输入任意词", "estimated_seconds": 30, "psychological_nudge": "不追求完美", "completion_criteria": "有字符出现"},
                {"step_order": 4, "action_description": "继续或停止", "estimated_seconds": 60, "psychological_nudge": "你有选择权", "completion_criteria": "完成或暂停"}
            ],
            "micro_momentum_score": 65,
            "hardware_context_isolation": {"hide_tabs": ["社交媒体"], "mute_notifications": True, "focus_window": "当前任务"},
            "emotional_stabilization": "检测到你有些分心。这是正常的，我们用2分钟重新启动。"
        })


# ============================================================
# L3: 微调度器引擎 (Micro Scheduler Engine)
# ============================================================

class MicroSchedulerEngine:
    """
    微调度器引擎 (L3)
    将大任务解耦为2-5分钟的微步骤链
    """
    
    SYSTEM_PROMPT = """你是"微调度器系统"。

将用户的大任务解耦为2-5分钟的微步骤链，每个步骤原子化、不可再分。

输出JSON：
{
  "decoupled_chain": [{"step_id": "", "action": "", "duration_seconds": 120, "psychological_note": ""}],
  "total_steps": 5,
  "estimated_total_minutes": 15,
  "noise_floor_level": 3,
  "context_isolation": {"ambient_noise": "", "notification_setting": "", "visual_clutter": ""}
}

设计原则：每个步骤2-5分钟，步骤间有明显完成感，提供停止点选择。"""

    def schedule(self, original_task: str, available_time_minutes: int = 30,
                 energy_level: int = 3) -> MicroSchedulerResult:
        """创建微调度计划"""
        context = f"任务: {original_task}\n可用时间: {available_time_minutes}分钟\n能量: {energy_level}/5"
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT, context, temperature=0.5)
            else:
                raw = self._mock_schedule(original_task)
            
            data = self._parse_json(raw)
            decoupled_chain = [DecoupledStep(
                step_id=s.get("step_id", str(uuid.uuid4())[:8]),
                action=s.get("action", ""),
                duration_seconds=s.get("duration_seconds", 180),
                completed=False
            ) for s in data.get("decoupled_chain", [])]
            
            return MicroSchedulerResult(
                session_id=str(uuid.uuid4()),
                original_task=original_task,
                decoupled_chain=decoupled_chain,
                current_step_index=0,
                noise_floor_level=data.get("noise_floor_level", 5),
                context_isolation_config=data.get("context_isolation", {}),
                momentum_score=0,
                completed_steps=0,
                total_steps=len(decoupled_chain)
            )
        except Exception as e:
            print(f"[MicroScheduler] Failed: {e}", flush=True)
            return self._fallback_schedule(original_task)
    
    def complete_step(self, scheduler_result: MicroSchedulerResult, step_index: int) -> MicroSchedulerResult:
        """完成指定步骤"""
        if 0 <= step_index < len(scheduler_result.decoupled_chain):
            scheduler_result.decoupled_chain[step_index].completed = True
            scheduler_result.current_step_index = step_index + 1
            scheduler_result.completed_steps = sum(1 for s in scheduler_result.decoupled_chain if s.completed)
            scheduler_result.momentum_score = int((scheduler_result.completed_steps / len(scheduler_result.decoupled_chain)) * 100)
        return scheduler_result
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except Exception:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try: return json.loads(m.strip())
                    except: continue
        return {}
    
    def _fallback_schedule(self, task: str) -> MicroSchedulerResult:
        steps = [
            DecoupledStep("step1", f"准备{task}环境", 120, False),
            DecoupledStep("step2", f"浏览{task}大纲", 180, False),
            DecoupledStep("step3", f"开始{task}第一部分", 300, False)
        ]
        return MicroSchedulerResult(
            session_id=str(uuid.uuid4()),
            original_task=task,
            decoupled_chain=steps,
            noise_floor_level=4,
            context_isolation_config={"ambient_noise": "白噪音", "notification_setting": "静音"},
            total_steps=len(steps)
        )
    
    def _mock_schedule(self, task: str) -> str:
        return json.dumps({
            "decoupled_chain": [
                {"step_id": "s1", "action": f"准备{task}所需材料", "duration_seconds": 120, "psychological_note": "只是准备，不开始执行"},
                {"step_id": "s2", "action": f"浏览{task}整体结构", "duration_seconds": 180, "psychological_note": "建立全局认知"},
                {"step_id": "s3", "action": f"完成{task}第一步", "duration_seconds": 300, "psychological_note": "专注一小段时间"}
            ],
            "total_steps": 3,
            "estimated_total_minutes": 10,
            "noise_floor_level": 3,
            "context_isolation": {"ambient_noise": "咖啡厅背景音", "notification_setting": "仅紧急通知", "visual_clutter": "清理无关窗口"}
        })


# ============================================================
# L4: 身份认同强化引擎 (Identity Reinforcement Engine)
# ============================================================

class IdentityReinforcementEngine:
    """
    身份认同强化引擎 (L4)
    长期身份认同塑造与迁移
    """
    
    POSITIVE_IDENTITIES = {
        "growth_continuity": [
            "我正在建立可持续的节奏",
            "每一次尝试都在强化我的系统",
            "成长是螺旋上升的，不必直线前进"
        ],
        "process_oriented": [
            "我专注于过程，结果自然到来",
            "我的价值在于持续的行动",
            "我在成为那种持续行动的人"
        ],
        "resilience_builder": [
            "我从挫折中恢复得越来越快",
            "困难是我系统的压力测试",
            "我有能力调整自己的策略"
        ],
        "long_term_investor": [
            "我是长期主义者",
            "我愿意为未来的自己投资",
            "时间是我的朋友"
        ],
        "self_mastery": [
            "我正在掌握自己的生活",
            "我有能力做出适合自己的选择",
            "我是自己人生的作者"
        ]
    }
    
    SYSTEM_PROMPT_IDENTITY = """你是"身份认同强化系统"。

分析用户数据，生成身份认同强化方案。

输出JSON：
{
  "current_narrative": "用户当前讲述的关于自己的故事",
  "narrative_type": "stable/improving/declining/transforming",
  "negative_identity_labels": ["负面标签1", "负面标签2"],
  "target_identity": "目标身份",
  "reinforcement_language": "强化语言",
  "long_term_migration": "长期迁移方向",
  "migration_progress": 50
}

原则：从"我失败了"到"我正在建立系统"的叙事转变。"""

    def reinforce_identity(self, user_history: list, recent_behaviors: list,
                           current_emotion_state: dict) -> IdentityReinforcementResult:
        """分析用户数据并生成身份认同强化方案"""
        context = "近期行为:\n" + "\n".join(f"- {b}" for b in recent_behaviors[-7:])
        context += f"\n情绪状态: {json.dumps(current_emotion_state, ensure_ascii=False)}"
        
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT_IDENTITY, context, temperature=0.5)
            else:
                raw = self._mock_identity_reinforcement()
            
            data = self._parse_json(raw)
            category = data.get("identity_category", "growth_continuity")
            reinforcement = data.get("reinforcement_language", "")
            if not reinforcement or len(reinforcement) < 10:
                reinforcement = self._select_reinforcement_language(category)
            
            return IdentityReinforcementResult(
                current_narrative=data.get("current_narrative", ""),
                narrative_type=data.get("narrative_type", "stable"),
                negative_identity_labels=data.get("negative_identity_labels", []),
                target_identity=data.get("target_identity", ""),
                reinforcement_language=reinforcement,
                long_term_migration=data.get("long_term_migration", ""),
                migration_progress=data.get("migration_progress", 50)
            )
        except Exception as e:
            print(f"[IdentityReinforcement] Failed: {e}", flush=True)
            return self._fallback_reinforcement()
    
    def deconstruct_negative_label(self, negative_label: str) -> dict:
        """解构负面身份标签"""
        prompt = f"解构负面标签'{negative_label}'。找出认知扭曲，提供反证据。输出JSON: {{'distortion_type': '', 'counter_evidence': [], 'reframed_identity': ''}}"
        try:
            if call_chat:
                raw = call_chat("你是认知重构专家", prompt, temperature=0.4)
                return self._parse_json(raw)
            return self._mock_deconstruction(negative_label)
        except Exception as e:
            print(f"[Deconstruct] Failed: {e}", flush=True)
            return {"distortion_type": "过度概括", "counter_evidence": ["你曾成功过"], "reframed_identity": "我在特定条件下会放慢节奏"}
    
    def _select_reinforcement_language(self, category: str) -> str:
        options = self.POSITIVE_IDENTITIES.get(category, self.POSITIVE_IDENTITIES["growth_continuity"])
        return random.choice(options)
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except Exception:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try: return json.loads(m.strip())
                    except: continue
        return {}
    
    def _fallback_reinforcement(self) -> IdentityReinforcementResult:
        return IdentityReinforcementResult(
            current_narrative="正在探索中的自我",
            narrative_type="stable",
            negative_identity_labels=[],
            target_identity="我是可以成长的人",
            reinforcement_language="你正在前进，这就是最重要的。",
            long_term_migration="建立可持续的行动系统",
            migration_progress=50
        )
    
    def _mock_identity_reinforcement(self) -> str:
        return json.dumps({
            "current_narrative": "我正在建立可持续的节奏",
            "narrative_type": "improving",
            "negative_identity_labels": [],
            "target_identity": "我是长期主义者",
            "reinforcement_language": "每一次尝试都在强化我的系统",
            "long_term_migration": "从短期爆发到持续行动",
            "migration_progress": 60,
            "identity_category": "long_term_investor"
        })
    
    def _mock_deconstruction(self, label: str) -> dict:
        return {"distortion_type": "标签化", "counter_evidence": ["你有成功时刻", "你在持续努力"], "reframed_identity": "我正在发展的过程中"}


# ============================================================
# 便捷函数 (Convenience Functions)
# ============================================================

# 引擎实例
behavior_regulation = BehaviorRegulationEngine()
habit_fsm = HabitStateMachineEngine()
habit_coordinator = HabitCoordinator()
edge_intervention = ExecutionEdgeInterventionEngine()
micro_scheduler = MicroSchedulerEngine()
identity_reinforcement = IdentityReinforcementEngine()


def regulate_behavior(task: str, energy: int = 3) -> dict:
    """便捷函数：行为调节（含属灵对齐评估）"""
    result = behavior_regulation.regulate(task, energy).to_dict()
    try:
        from backend.spiritual_alignment import assess_spiritual_alignment
        result["spiritual_alignment"] = assess_spiritual_alignment(task)
    except Exception as e:
        print(f'[regulate_behavior] Spiritual alignment failed: {e}', flush=True)
        result["spiritual_alignment"] = {
            "aligned": True,
            "alignment_score": 50,
            "assessment": "属灵对齐评估暂不可用，请稍后重试或联系管理员",
            "scripture_reference": "箴3:5-6",
            "principle": "你要专心仰赖耶和华，不可倚靠自己的聪明",
            "misalignment_areas": [],
            "alignment_actions": ["检查后端服务是否正常运行", "刷新页面后重试"],
            "category": "评估异常"
        }
    return result


def create_habit(habit_name: str, anchor: str = "", energy: int = 3) -> dict:
    """便捷函数：创建并执行习惯"""
    return habit_coordinator.create_and_execute(habit_name, energy, anchor)


def execute_habit_fsm(habit_config: dict, energy: int = 3) -> dict:
    """便捷函数：执行习惯状态机"""
    return habit_fsm.execute_habit(habit_config, energy).to_dict()


def intervene_edge(task: str, signals: list, context: dict) -> dict:
    """便捷函数：执行力边缘干预"""
    return edge_intervention.intervene(task, signals, context).to_dict()


def schedule_micro_task(task: str, minutes: int = 30, energy: int = 3) -> dict:
    """便捷函数：微任务调度"""
    return micro_scheduler.schedule(task, minutes, energy).to_dict()


def reinforce_user_identity(history: list, behaviors: list, emotion: dict) -> dict:
    """便捷函数：身份认同强化"""
    return identity_reinforcement.reinforce_identity(history, behaviors, emotion).to_dict()


# 版本信息
__version__ = "1.0.0"
__all__ = [
    "BehaviorRegulationEngine", "BehaviorRegulationResult",
    "HabitStateMachineEngine", "HabitStateMachineResult", "HabitCoordinator",
    "ExecutionEdgeInterventionEngine", "ExecutionEdgeInterventionResult",
    "MicroSchedulerEngine", "MicroSchedulerResult",
    "IdentityReinforcementEngine", "IdentityReinforcementResult",
    "regulate_behavior", "create_habit", "execute_habit_fsm",
    "intervene_edge", "schedule_micro_task", "reinforce_user_identity",
    "set_call_chat_fn"
]
