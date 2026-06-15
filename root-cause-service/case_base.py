def _generate_evolution_curves():
    curves = {}
    t = [i / 19.0 for i in range(20)]

    # CASE-PUMP-001 轴承磨损：振动前段缓升+后段急升，温度中等上升
    curves["CASE-PUMP-001"] = {
        "vibration": [_clip(0.2 + 0.3 * x + 0.5 * (x ** 3)) for x in t],
        "temperature": [_clip(0.3 + 0.4 * (x ** 1.5)) for x in t],
        "current": [_clip(0.2 + 0.15 * x) for x in t],
        "speed": [_clip(0.1 + 0.05 * x) for x in t],
        "acoustic": [_clip(0.25 + 0.35 * (x ** 2)) for x in t],
    }

    # CASE-PUMP-002 叶轮堵塞：电流先升后升速，转速先稳后降
    curves["CASE-PUMP-002"] = {
        "vibration": [_clip(0.25 + 0.2 * x) for x in t],
        "temperature": [_clip(0.2 + 0.15 * x) for x in t],
        "current": [_clip(0.3 + 0.2 * x + 0.35 * (x ** 2)) for x in t],
        "speed": [_clip(0.6 - 0.4 * (x ** 2)) for x in t],
        "acoustic": [_clip(0.2 + 0.15 * (x ** 1.2)) for x in t],
    }

    # CASE-PUMP-003 机械密封泄漏：温度中等上升，振动轻微，声发射低缓
    curves["CASE-PUMP-003"] = {
        "vibration": [_clip(0.15 + 0.12 * x) for x in t],
        "temperature": [_clip(0.35 + 0.25 * (x ** 1.3)) for x in t],
        "current": [_clip(0.1 + 0.1 * x) for x in t],
        "speed": [_clip(0.05 + 0.03 * x) for x in t],
        "acoustic": [_clip(0.2 + 0.1 * (x ** 1.1)) for x in t],
    }

    # CASE-PUMP-004 气蚀故障：声发射突然跳升，振动中等波动
    curves["CASE-PUMP-004"] = {
        "vibration": [_clip(0.35 + 0.2 * (x ** 1.5) + 0.05 * ((-1) ** i)) for i, x in enumerate(t)],
        "temperature": [_clip(0.15 + 0.1 * x) for x in t],
        "current": [_clip(0.2 + 0.1 * x) for x in t],
        "speed": [_clip(0.05 + 0.05 * x) for x in t],
        "acoustic": [_clip(0.15 + 0.1 * x if x < 0.5 else 0.2 + 0.65 * (x - 0.5) ** 0.8 + 0.15) for x in t],
    }

    # CASE-FAN-001 叶轮积灰失衡：振动持续升高且加速，其他较平
    curves["CASE-FAN-001"] = {
        "vibration": [_clip(0.35 + 0.2 * x + 0.4 * (x ** 2.5)) for x in t],
        "temperature": [_clip(0.15 + 0.08 * x) for x in t],
        "current": [_clip(0.2 + 0.15 * x) for x in t],
        "speed": [_clip(0.1 + 0.06 * x) for x in t],
        "acoustic": [_clip(0.25 + 0.2 * (x ** 1.3)) for x in t],
    }

    # CASE-FAN-002 皮带松动打滑：转速持续下降，声发射上升
    curves["CASE-FAN-002"] = {
        "vibration": [_clip(0.25 + 0.15 * x) for x in t],
        "temperature": [_clip(0.25 + 0.15 * (x ** 1.2)) for x in t],
        "current": [_clip(0.15 + 0.1 * x) for x in t],
        "speed": [_clip(0.75 - 0.55 * (x ** 1.5)) for x in t],
        "acoustic": [_clip(0.3 + 0.3 * (x ** 1.4)) for x in t],
    }

    # CASE-FAN-003 轴承润滑不足：温度持续上升后急升，振动缓慢上升
    curves["CASE-FAN-003"] = {
        "vibration": [_clip(0.3 + 0.2 * (x ** 1.5)) for x in t],
        "temperature": [_clip(0.4 + 0.3 * x + 0.3 * (x ** 4)) for x in t],
        "current": [_clip(0.15 + 0.12 * x) for x in t],
        "speed": [_clip(0.05 + 0.04 * x) for x in t],
        "acoustic": [_clip(0.3 + 0.25 * (x ** 1.6)) for x in t],
    }

    # CASE-FAN-004 风道阻力过大：电流较高缓升，转速中等
    curves["CASE-FAN-004"] = {
        "vibration": [_clip(0.1 + 0.08 * x) for x in t],
        "temperature": [_clip(0.15 + 0.1 * x) for x in t],
        "current": [_clip(0.5 + 0.3 * (x ** 1.3)) for x in t],
        "speed": [_clip(0.4 + 0.1 * x - 0.05 * (x ** 2)) for x in t],
        "acoustic": [_clip(0.2 + 0.1 * (x ** 1.1)) for x in t],
    }

    # CASE-MOTOR-001 电机过载：电流持续攀升，温度高
    curves["CASE-MOTOR-001"] = {
        "vibration": [_clip(0.2 + 0.12 * x) for x in t],
        "temperature": [_clip(0.55 + 0.3 * (x ** 1.4)) for x in t],
        "current": [_clip(0.6 + 0.35 * (x ** 1.2)) for x in t],
        "speed": [_clip(0.45 - 0.25 * (x ** 1.5)) for x in t],
        "acoustic": [_clip(0.25 + 0.15 * (x ** 1.2)) for x in t],
    }

    # CASE-MOTOR-002 绕组绝缘老化：温度缓慢持续上升，电流中等波动上升
    curves["CASE-MOTOR-002"] = {
        "vibration": [_clip(0.1 + 0.1 * x) for x in t],
        "temperature": [_clip(0.4 + 0.35 * (x ** 1.8)) for x in t],
        "current": [_clip(0.35 + 0.15 * x + 0.08 * (x ** 2)) for x in t],
        "speed": [_clip(0.1 + 0.04 * x) for x in t],
        "acoustic": [_clip(0.12 + 0.1 * (x ** 1.1)) for x in t],
    }

    # CASE-MOTOR-003 转子断条：振动和电流有明显波动
    curves["CASE-MOTOR-003"] = {
        "vibration": [_clip(0.4 + 0.25 * (x ** 1.3) + 0.08 * ((-1) ** i)) for i, x in enumerate(t)],
        "temperature": [_clip(0.3 + 0.2 * (x ** 1.2)) for x in t],
        "current": [_clip(0.35 + 0.2 * x + 0.1 * ((-1) ** i) * 0.5) for i, x in enumerate(t)],
        "speed": [_clip(0.35 + 0.08 * x + 0.06 * ((-1) ** i) * 0.3) for i, x in enumerate(t)],
        "acoustic": [_clip(0.3 + 0.2 * (x ** 1.3)) for x in t],
    }

    # CASE-MOTOR-004 冷却风扇损坏：温度快速上升，声发射中等
    curves["CASE-MOTOR-004"] = {
        "vibration": [_clip(0.2 + 0.15 * (x ** 1.2)) for x in t],
        "temperature": [_clip(0.5 + 0.45 * (x ** 2)) for x in t],
        "current": [_clip(0.15 + 0.1 * x) for x in t],
        "speed": [_clip(0.03 + 0.02 * x) for x in t],
        "acoustic": [_clip(0.4 + 0.3 * (x ** 1.5)) for x in t],
    }

    # CASE-MOTOR-005 轴承缺油抱死：全特征剧烈上升
    curves["CASE-MOTOR-005"] = {
        "vibration": [_clip(0.3 + 0.25 * (x ** 2) + 0.35 * (x ** 4)) for x in t],
        "temperature": [_clip(0.4 + 0.3 * (x ** 2) + 0.3 * (x ** 5)) for x in t],
        "current": [_clip(0.3 + 0.25 * (x ** 2.5)) for x in t],
        "speed": [_clip(0.6 + 0.1 * x - 0.5 * (x ** 3)) for x in t],
        "acoustic": [_clip(0.35 + 0.3 * (x ** 2) + 0.25 * (x ** 4)) for x in t],
    }

    # CASE-COMP-001 排气阀片损坏：声发射尖峰，振动中等
    curves["CASE-COMP-001"] = {
        "vibration": [_clip(0.35 + 0.25 * (x ** 1.4)) for x in t],
        "temperature": [_clip(0.35 + 0.25 * (x ** 1.3)) for x in t],
        "current": [_clip(0.25 + 0.2 * x) for x in t],
        "speed": [_clip(0.06 + 0.04 * x) for x in t],
        "acoustic": [_clip(0.25 + 0.15 * x if x < 0.4 else 0.31 + 0.55 * ((x - 0.4) / 0.6) ** 1.5) for x in t],
    }

    # CASE-COMP-002 活塞环磨损：电流持续上升，温度中等
    curves["CASE-COMP-002"] = {
        "vibration": [_clip(0.2 + 0.15 * (x ** 1.2)) for x in t],
        "temperature": [_clip(0.35 + 0.25 * (x ** 1.4)) for x in t],
        "current": [_clip(0.4 + 0.35 * (x ** 1.5)) for x in t],
        "speed": [_clip(0.04 + 0.03 * x) for x in t],
        "acoustic": [_clip(0.2 + 0.18 * (x ** 1.2)) for x in t],
    }

    # CASE-COMP-003 润滑油超温：温度极高，其他较低
    curves["CASE-COMP-003"] = {
        "vibration": [_clip(0.1 + 0.1 * x) for x in t],
        "temperature": [_clip(0.55 + 0.4 * (x ** 1.6)) for x in t],
        "current": [_clip(0.15 + 0.1 * x) for x in t],
        "speed": [_clip(0.03 + 0.02 * x) for x in t],
        "acoustic": [_clip(0.08 + 0.08 * x) for x in t],
    }

    # CASE-COMP-004 空气过滤器堵塞：电流偏高缓升，其他低
    curves["CASE-COMP-004"] = {
        "vibration": [_clip(0.08 + 0.06 * x) for x in t],
        "temperature": [_clip(0.2 + 0.12 * (x ** 1.1)) for x in t],
        "current": [_clip(0.4 + 0.3 * (x ** 1.2)) for x in t],
        "speed": [_clip(0.05 + 0.04 * x) for x in t],
        "acoustic": [_clip(0.2 + 0.12 * (x ** 1.1)) for x in t],
    }

    # CASE-CONV-001 皮带跑偏：振动中等，声发射中等
    curves["CASE-CONV-001"] = {
        "vibration": [_clip(0.25 + 0.2 * (x ** 1.3)) for x in t],
        "temperature": [_clip(0.15 + 0.12 * x) for x in t],
        "current": [_clip(0.2 + 0.15 * x) for x in t],
        "speed": [_clip(0.15 + 0.07 * x) for x in t],
        "acoustic": [_clip(0.3 + 0.2 * (x ** 1.2)) for x in t],
    }

    # CASE-CONV-002 托辊卡滞不转：声发射高，振动中等
    curves["CASE-CONV-002"] = {
        "vibration": [_clip(0.3 + 0.22 * (x ** 1.3)) for x in t],
        "temperature": [_clip(0.3 + 0.2 * (x ** 1.4)) for x in t],
        "current": [_clip(0.15 + 0.12 * x) for x in t],
        "speed": [_clip(0.06 + 0.04 * x) for x in t],
        "acoustic": [_clip(0.4 + 0.3 * (x ** 1.5)) for x in t],
    }

    # CASE-CONV-003 减速器齿轮磨损：振动高，声发射高
    curves["CASE-CONV-003"] = {
        "vibration": [_clip(0.4 + 0.3 * (x ** 1.5) + 0.12 * ((-1) ** i) * 0.5) for i, x in enumerate(t)],
        "temperature": [_clip(0.3 + 0.25 * (x ** 1.3)) for x in t],
        "current": [_clip(0.2 + 0.18 * x) for x in t],
        "speed": [_clip(0.1 + 0.08 * x) for x in t],
        "acoustic": [_clip(0.4 + 0.35 * (x ** 1.6)) for x in t],
    }

    # CASE-CONV-004 张紧装置失效：转速下降明显，电流中等
    curves["CASE-CONV-004"] = {
        "vibration": [_clip(0.25 + 0.2 * (x ** 1.2)) for x in t],
        "temperature": [_clip(0.1 + 0.08 * x) for x in t],
        "current": [_clip(0.3 + 0.2 * (x ** 1.3)) for x in t],
        "speed": [_clip(0.55 - 0.35 * (x ** 1.5)) for x in t],
        "acoustic": [_clip(0.25 + 0.15 * (x ** 1.1)) for x in t],
    }

    # CASE-CONV-005 滚筒轴承损坏：振动极高，温度高
    curves["CASE-CONV-005"] = {
        "vibration": [_clip(0.35 + 0.3 * (x ** 1.5) + 0.3 * (x ** 3.5)) for x in t],
        "temperature": [_clip(0.4 + 0.35 * (x ** 1.8)) for x in t],
        "current": [_clip(0.25 + 0.2 * (x ** 1.2)) for x in t],
        "speed": [_clip(0.1 + 0.05 * x) for x in t],
        "acoustic": [_clip(0.35 + 0.3 * (x ** 1.5)) for x in t],
    }

    return curves


def _clip(v):
    return round(max(0.0, min(1.0, v)), 4)


class CaseBase:
    def __init__(self):
        self._cases = []
        self._initialize_default_cases()

    def _initialize_default_cases(self):
        evolution_curves = _generate_evolution_curves()

        self._cases = [
            {
                "case_id": "CASE-PUMP-001",
                "device_type": "pump",
                "fault_type": "轴承磨损",
                "symptoms": {
                    "vibration": 0.85,
                    "temperature": 0.72,
                    "current": 0.45,
                    "speed": 0.15,
                    "acoustic": 0.78
                },
                "evolution_curves": evolution_curves["CASE-PUMP-001"],
                "root_cause": "泵轴承长期运行缺乏润滑，滚道和滚动体产生疲劳点蚀和磨损，导致振动加剧和温度升高",
                "solution": "立即停机更换轴承，检查润滑系统是否正常，补充或更换润滑脂，检查轴承座对中情况",
                "severity": 4,
                "occurrence_count": 47
            },
            {
                "case_id": "CASE-PUMP-002",
                "device_type": "pump",
                "fault_type": "叶轮堵塞",
                "symptoms": {
                    "vibration": 0.55,
                    "temperature": 0.35,
                    "current": 0.82,
                    "speed": 0.68,
                    "acoustic": 0.42
                },
                "evolution_curves": evolution_curves["CASE-PUMP-002"],
                "root_cause": "输送介质中含有杂质或结晶物，堆积在叶轮流道内，造成叶轮不平衡和流量下降，电机过载",
                "solution": "拆卸泵体，清理叶轮和蜗壳流道，检查入口过滤器是否破损，必要时加装更精密的过滤装置",
                "severity": 3,
                "occurrence_count": 38
            },
            {
                "case_id": "CASE-PUMP-003",
                "device_type": "pump",
                "fault_type": "机械密封泄漏",
                "symptoms": {
                    "vibration": 0.28,
                    "temperature": 0.58,
                    "current": 0.22,
                    "speed": 0.08,
                    "acoustic": 0.35
                },
                "evolution_curves": evolution_curves["CASE-PUMP-003"],
                "root_cause": "机械密封动环与静环摩擦面磨损或O型圈老化，导致密封失效，介质泄漏伴随局部温度升高",
                "solution": "更换机械密封组件，检查密封腔冷却冲洗管路，确认介质中无颗粒性杂质",
                "severity": 3,
                "occurrence_count": 29
            },
            {
                "case_id": "CASE-PUMP-004",
                "device_type": "pump",
                "fault_type": "气蚀故障",
                "symptoms": {
                    "vibration": 0.72,
                    "temperature": 0.28,
                    "current": 0.38,
                    "speed": 0.12,
                    "acoustic": 0.88
                },
                "evolution_curves": evolution_curves["CASE-PUMP-004"],
                "root_cause": "泵入口压力低于介质饱和蒸气压，产生气泡溃灭造成叶轮表面点蚀，伴随强烈异常噪声",
                "solution": "提高入口液位高度，降低介质温度，检查入口管路是否堵塞，减小流量运行或更换抗气蚀叶轮",
                "severity": 4,
                "occurrence_count": 21
            },
            {
                "case_id": "CASE-FAN-001",
                "device_type": "fan",
                "fault_type": "叶轮积灰失衡",
                "symptoms": {
                    "vibration": 0.90,
                    "temperature": 0.25,
                    "current": 0.42,
                    "speed": 0.18,
                    "acoustic": 0.55
                },
                "evolution_curves": evolution_curves["CASE-FAN-001"],
                "root_cause": "风机长期运行，粉尘在叶片表面积灰不均，造成叶轮动平衡严重破坏，振动随转速加剧",
                "solution": "停机清理叶轮表面积灰，做动平衡校验，检查风道过滤装置，必要时增加在线清灰装置",
                "severity": 4,
                "occurrence_count": 56
            },
            {
                "case_id": "CASE-FAN-002",
                "device_type": "fan",
                "fault_type": "皮带松动打滑",
                "symptoms": {
                    "vibration": 0.48,
                    "temperature": 0.45,
                    "current": 0.28,
                    "speed": 0.85,
                    "acoustic": 0.62
                },
                "evolution_curves": evolution_curves["CASE-FAN-002"],
                "root_cause": "传动皮带长期使用磨损伸长，张紧度不足，皮带与带轮之间打滑，转速下降且伴随啸叫声",
                "solution": "调整皮带张紧力或更换新皮带，检查带轮对中和磨损情况，更换磨损严重的带轮",
                "severity": 2,
                "occurrence_count": 42
            },
            {
                "case_id": "CASE-FAN-003",
                "device_type": "fan",
                "fault_type": "轴承润滑不足",
                "symptoms": {
                    "vibration": 0.68,
                    "temperature": 0.88,
                    "current": 0.35,
                    "speed": 0.10,
                    "acoustic": 0.65
                },
                "evolution_curves": evolution_curves["CASE-FAN-003"],
                "root_cause": "轴承润滑脂干涸或不足，滚动体与滚道干摩擦，温度急剧升高，振动和噪声增大",
                "solution": "补充耐高温润滑脂，若温度持续升高需更换轴承，检查轴承迷宫密封是否完好",
                "severity": 4,
                "occurrence_count": 33
            },
            {
                "case_id": "CASE-FAN-004",
                "device_type": "fan",
                "fault_type": "风道阻力过大",
                "symptoms": {
                    "vibration": 0.22,
                    "temperature": 0.30,
                    "current": 0.78,
                    "speed": 0.55,
                    "acoustic": 0.38
                },
                "evolution_curves": evolution_curves["CASE-FAN-004"],
                "root_cause": "风道挡板关闭、过滤器堵塞或管道变形，导致风机工作点偏移至高压区，电流增大",
                "solution": "检查并全开风道挡板，清理或更换空气过滤器，检查风管道是否有变形堵塞",
                "severity": 2,
                "occurrence_count": 27
            },
            {
                "case_id": "CASE-MOTOR-001",
                "device_type": "motor",
                "fault_type": "电机过载",
                "symptoms": {
                    "vibration": 0.38,
                    "temperature": 0.82,
                    "current": 0.92,
                    "speed": 0.52,
                    "acoustic": 0.48
                },
                "evolution_curves": evolution_curves["CASE-MOTOR-001"],
                "root_cause": "负载超出电机额定功率，或机械卡滞导致电机电流超限，绕组过热，转速下降",
                "solution": "检查负载机械是否有卡滞，调整负载至合理范围，检查电机散热风扇是否正常，必要时更换大功率电机",
                "severity": 4,
                "occurrence_count": 51
            },
            {
                "case_id": "CASE-MOTOR-002",
                "device_type": "motor",
                "fault_type": "绕组绝缘老化",
                "symptoms": {
                    "vibration": 0.25,
                    "temperature": 0.75,
                    "current": 0.58,
                    "speed": 0.15,
                    "acoustic": 0.28
                },
                "evolution_curves": evolution_curves["CASE-MOTOR-002"],
                "root_cause": "电机长期高温运行，绕组绝缘材料热老化，匝间绝缘电阻下降，电流不平衡且温度升高",
                "solution": "做绝缘电阻测试确认老化程度，轻微者进行浸漆烘干处理，严重者需重新绕线或更换电机",
                "severity": 5,
                "occurrence_count": 19
            },
            {
                "case_id": "CASE-MOTOR-003",
                "device_type": "motor",
                "fault_type": "转子断条",
                "symptoms": {
                    "vibration": 0.78,
                    "temperature": 0.55,
                    "current": 0.62,
                    "speed": 0.48,
                    "acoustic": 0.58
                },
                "evolution_curves": evolution_curves["CASE-MOTOR-003"],
                "root_cause": "铸铝转子导条断裂，造成三相电流不平衡，转速波动，电磁振动呈现明显极通过特征",
                "solution": "做转子断条检测（电流频谱或零电压测试），确认后更换转子总成",
                "severity": 4,
                "occurrence_count": 15
            },
            {
                "case_id": "CASE-MOTOR-004",
                "device_type": "motor",
                "fault_type": "冷却风扇损坏",
                "symptoms": {
                    "vibration": 0.42,
                    "temperature": 0.90,
                    "current": 0.35,
                    "speed": 0.05,
                    "acoustic": 0.72
                },
                "evolution_curves": evolution_curves["CASE-MOTOR-004"],
                "root_cause": "电机尾端冷却风扇叶片断裂或脱落，冷却风量不足，电机整体过热，伴随风路异常噪声",
                "solution": "更换冷却风扇，检查风扇罩是否变形，清理电机散热筋表面积灰和油污",
                "severity": 3,
                "occurrence_count": 24
            },
            {
                "case_id": "CASE-MOTOR-005",
                "device_type": "motor",
                "fault_type": "轴承缺油抱死",
                "symptoms": {
                    "vibration": 0.88,
                    "temperature": 0.95,
                    "current": 0.72,
                    "speed": 0.78,
                    "acoustic": 0.82
                },
                "evolution_curves": evolution_curves["CASE-MOTOR-005"],
                "root_cause": "电机前后轴承严重缺油，润滑脂碳化，轴承抱死导致电机堵转，电流剧增，即将烧毁",
                "solution": "紧急断电停机，强制冷却后拆解检查，更换全部轴承，清理轴承腔，充注合格润滑脂，检查端盖同轴度",
                "severity": 5,
                "occurrence_count": 11
            },
            {
                "case_id": "CASE-COMP-001",
                "device_type": "compressor",
                "fault_type": "排气阀片损坏",
                "symptoms": {
                    "vibration": 0.72,
                    "temperature": 0.68,
                    "current": 0.55,
                    "speed": 0.12,
                    "acoustic": 0.80
                },
                "evolution_curves": evolution_curves["CASE-COMP-001"],
                "root_cause": "压缩机排气阀片疲劳断裂或变形，造成气体倒流，排气压力不足，伴随清脆的金属敲击声",
                "solution": "拆卸气缸盖更换进排气阀组，检查阀片材质是否达标，清理阀座密封面，检查气体中是否有液体带入",
                "severity": 4,
                "occurrence_count": 31
            },
            {
                "case_id": "CASE-COMP-002",
                "device_type": "compressor",
                "fault_type": "活塞环磨损",
                "symptoms": {
                    "vibration": 0.45,
                    "temperature": 0.62,
                    "current": 0.75,
                    "speed": 0.08,
                    "acoustic": 0.48
                },
                "evolution_curves": evolution_curves["CASE-COMP-002"],
                "root_cause": "活塞环长期磨损，密封性能下降，高低压腔串气，排气量降低，电流增大，油温升高",
                "solution": "拆解更换活塞环及配套活塞，检查气缸内壁磨损情况，超差时镗缸或更换气缸套",
                "severity": 3,
                "occurrence_count": 26
            },
            {
                "case_id": "CASE-COMP-003",
                "device_type": "compressor",
                "fault_type": "润滑油超温",
                "symptoms": {
                    "vibration": 0.25,
                    "temperature": 0.92,
                    "current": 0.32,
                    "speed": 0.05,
                    "acoustic": 0.20
                },
                "evolution_curves": evolution_curves["CASE-COMP-003"],
                "root_cause": "冷却器结垢堵塞或温控阀失灵，润滑油散热不良，油温超过报警值，加速油品氧化",
                "solution": "清洗油冷却器管束，检查温控阀阀芯动作是否正常，更换老化变质的润滑油，检查油路过滤器",
                "severity": 3,
                "occurrence_count": 35
            },
            {
                "case_id": "CASE-COMP-004",
                "device_type": "compressor",
                "fault_type": "空气过滤器堵塞",
                "symptoms": {
                    "vibration": 0.18,
                    "temperature": 0.38,
                    "current": 0.68,
                    "speed": 0.10,
                    "acoustic": 0.42
                },
                "evolution_curves": evolution_curves["CASE-COMP-004"],
                "root_cause": "吸气过滤器积灰堵塞，吸气阻力增大，吸气负压过高，排气量下降，电流偏高",
                "solution": "清理或更换空气滤芯，检查过滤棉是否需要更换，评估环境粉尘浓度，必要时增加前置过滤",
                "severity": 2,
                "occurrence_count": 44
            },
            {
                "case_id": "CASE-CONV-001",
                "device_type": "conveyor",
                "fault_type": "皮带跑偏",
                "symptoms": {
                    "vibration": 0.48,
                    "temperature": 0.35,
                    "current": 0.42,
                    "speed": 0.25,
                    "acoustic": 0.55
                },
                "evolution_curves": evolution_curves["CASE-CONV-001"],
                "root_cause": "托辊安装不正、落料点偏置或皮带接头不正，导致皮带沿纵向跑偏，边缘与机架摩擦",
                "solution": "调整头尾轮对中，检查托辊转动是否灵活，加装调心托辊，校正落料点位置在皮带中心",
                "severity": 2,
                "occurrence_count": 63
            },
            {
                "case_id": "CASE-CONV-002",
                "device_type": "conveyor",
                "fault_type": "托辊卡滞不转",
                "symptoms": {
                    "vibration": 0.62,
                    "temperature": 0.58,
                    "current": 0.38,
                    "speed": 0.12,
                    "acoustic": 0.68
                },
                "evolution_curves": evolution_curves["CASE-CONV-002"],
                "root_cause": "托辊轴承缺油或进水损坏，托辊不转与皮带滑动摩擦，造成局部高温和异常噪声",
                "solution": "逐段检查更换卡滞托辊，选用密封型优质托辊，改进托辊润滑方式，避免水淋和粉尘侵入",
                "severity": 3,
                "occurrence_count": 48
            },
            {
                "case_id": "CASE-CONV-003",
                "device_type": "conveyor",
                "fault_type": "减速器齿轮磨损",
                "symptoms": {
                    "vibration": 0.82,
                    "temperature": 0.65,
                    "current": 0.48,
                    "speed": 0.22,
                    "acoustic": 0.75
                },
                "evolution_curves": evolution_curves["CASE-CONV-003"],
                "root_cause": "减速器齿轮齿面点蚀、胶合或磨损严重，齿侧间隙超标，产生冲击振动和周期性啮合噪声",
                "solution": "检查齿轮磨损程度，轻者更换齿轮油并调整间隙，严重时更换磨损齿轮副，检查润滑油冷却系统",
                "severity": 4,
                "occurrence_count": 22
            },
            {
                "case_id": "CASE-CONV-004",
                "device_type": "conveyor",
                "fault_type": "张紧装置失效",
                "symptoms": {
                    "vibration": 0.52,
                    "temperature": 0.22,
                    "current": 0.52,
                    "speed": 0.65,
                    "acoustic": 0.48
                },
                "evolution_curves": evolution_curves["CASE-CONV-004"],
                "root_cause": "重锤张紧装置卡死或螺旋张紧松动，皮带张紧力不足，启动和负载时打滑，转速波动",
                "solution": "修复张紧装置动作灵活性，调整张紧力至设计值，检查皮带是否伸长超限，必要时截短重做接头",
                "severity": 3,
                "occurrence_count": 30
            },
            {
                "case_id": "CASE-CONV-005",
                "device_type": "conveyor",
                "fault_type": "滚筒轴承损坏",
                "symptoms": {
                    "vibration": 0.88,
                    "temperature": 0.80,
                    "current": 0.55,
                    "speed": 0.18,
                    "acoustic": 0.70
                },
                "evolution_curves": evolution_curves["CASE-CONV-005"],
                "root_cause": "传动滚筒或改向滚筒轴承过载损坏，伴随强烈低频振动和轴承部位高温",
                "solution": "更换滚筒轴承，检查轴承座对中和滚筒是否变形，计算轴承额定寿命是否满足要求",
                "severity": 4,
                "occurrence_count": 17
            }
        ]

    def get_all_cases(self):
        return [case.copy() for case in self._cases]

    def get_cases_by_device_type(self, device_type):
        return [case.copy() for case in self._cases if case["device_type"].lower() == device_type.lower()]

    def add_case(self, case_data):
        required_fields = ["case_id", "device_type", "fault_type", "symptoms",
                           "root_cause", "solution", "severity", "occurrence_count"]
        for field in required_fields:
            if field not in case_data:
                raise ValueError(f"Missing required field: {field}")

        symptom_fields = ["vibration", "temperature", "current", "speed", "acoustic"]
        for field in symptom_fields:
            if field not in case_data["symptoms"]:
                raise ValueError(f"Missing symptom field: {field}")

        if not (1 <= case_data["severity"] <= 5):
            raise ValueError("Severity must be between 1 and 5")

        self._cases.append(case_data.copy())
        return case_data["case_id"]

    def get_case_count(self):
        return len(self._cases)

    def get_device_types(self):
        return list(set(case["device_type"] for case in self._cases))
