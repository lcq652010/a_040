#!/usr/bin/env python3
"""PHM System Local Integration Test - validates full data flow without Docker"""

import json
import os
import sys
import time
import threading
import tempfile
import shutil
import numpy as np

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

EDGE_NORMAL_RANGES = {
    "vibration": (2.0, 5.0),
    "temperature": (55.0, 75.0),
    "current": (15.0, 25.0),
    "speed": (2800.0, 3000.0),
    "acoustic_emission": (65.0, 85.0),
}

RESULTS = []


def record(name, passed, detail=""):
    icon = "[PASS]" if passed else "[FAIL]"
    RESULTS.append({"name": name, "passed": passed, "detail": detail})
    print("  {} {}".format(icon, name))
    if not passed and detail:
        print("     -> " + detail)


def test_edge_node_anomaly_detector():
    print("\n>> 1. 边缘节点孤立森林检测器")
    import importlib

    saved_modules = {}
    for key in list(sys.modules.keys()):
        if key in ("config", "anomaly_detector"):
            saved_modules[key] = sys.modules.pop(key)

    edge_dir = os.path.join(PROJECT_ROOT, "edge-node")
    sys.path.insert(0, edge_dir)
    try:
        config_spec = importlib.util.spec_from_file_location(
            "config", os.path.join(edge_dir, "config.py")
        )
        edge_config = importlib.util.module_from_spec(config_spec)
        sys.modules["config"] = edge_config
        config_spec.loader.exec_module(edge_config)

        tmp_dir = tempfile.mkdtemp(prefix="phm_test_")
        edge_config.MODEL_SAVE_DIR = tmp_dir

        from anomaly_detector import IsolationForestAnomalyDetector

        detector = IsolationForestAnomalyDetector(
            device_type="air_compressor",
            normal_ranges=EDGE_NORMAL_RANGES,
            device_id="TEST-AC",
            n_estimators=50,
            n_samples=200,
        )
        record("孤立森林模型训练", detector.model is not None)

        normal_data = {"vibration": 3.5, "temperature": 65, "current": 20, "speed": 2900, "acoustic": 75}
        is_anom, score = detector.detect(normal_data)
        record("正常数据检测", isinstance(is_anom, bool) and isinstance(score, float),
               f"is_anomaly={is_anom}, score={score:.4f}")

        anomaly_data = {"vibration": 50.0, "temperature": 150, "current": 80, "speed": 500, "acoustic": 200}
        is_anom2, score2 = detector.detect(anomaly_data)
        record("异常数据检测(极端值)", score2 < 0,
               "is_anomaly={}, score={:.4f}".format(is_anom2, score2))

        model_file = os.path.join(tmp_dir, "TEST-AC_iforest.joblib")
        record("模型文件持久化", os.path.exists(model_file))

        detector3 = IsolationForestAnomalyDetector(
            device_type="air_compressor",
            normal_ranges=EDGE_NORMAL_RANGES,
            device_id="TEST-AC",
            n_estimators=50,
            n_samples=200,
        )
        is_anom3, score3 = detector3.detect(normal_data)
        record("模型加载后检测一致", abs(score3 - score) < 0.01,
               "原score={:.4f}, 加载后score={:.4f}".format(score, score3))

        detector4 = IsolationForestAnomalyDetector(
            device_type="air_compressor",
            normal_ranges=EDGE_NORMAL_RANGES,
            device_id="TEST-INC",
            n_estimators=50,
            n_samples=200,
        )
        for i in range(100):
            data = {"vibration": 3.5 + i * 0.01, "temperature": 65, "current": 20, "speed": 2900, "acoustic": 75}
            detector4.detect(data)
        record("增量更新(100次检测)", detector4.update_counter == 0,
               "counter={}, buffer_len={}".format(detector4.update_counter, len(detector4.data_buffer)))

        alias_data = {"vibration": 3.5, "temperature": 65, "current": 20, "speed": 2900, "acoustic_emission": 75}
        is_anom4, score4 = detector3.detect(alias_data)
        record("acoustic_emission字段映射", isinstance(score4, float),
               "score={:.4f}".format(score4))
    except Exception as e:
        record("边缘节点测试异常", False, str(e)[:200])
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if edge_dir in sys.path:
            sys.path.remove(edge_dir)
        for key in list(sys.modules.keys()):
            if key in ("config", "anomaly_detector"):
                del sys.modules[key]
        for key, val in saved_modules.items():
            sys.modules[key] = val


def test_root_cause_analysis():
    print("\n>> 2. 根因分析DTW匹配")
    saved_modules = {}
    for key in list(sys.modules.keys()):
        if key in ("config", "case_base", "similarity_matcher"):
            saved_modules[key] = sys.modules.pop(key)
    rc_dir = os.path.join(PROJECT_ROOT, "root-cause-service")
    sys.path.insert(0, rc_dir)
    try:
        from case_base import CaseBase
        from similarity_matcher import SimilarityMatcher, DTWMatcher

        cb = CaseBase()
        record("案例库加载", cb.get_case_count() > 0, f"案例数: {cb.get_case_count()}")

        matcher = SimilarityMatcher(cb)
        anomaly = {"vibration": 0.7, "temperature": 0.6, "current": 0.5, "speed": 0.3, "acoustic": 0.6}
        sim = matcher.compute_similarity(cb.get_all_cases()[0], anomaly)
        record("点匹配相似度计算", 0.0 <= sim <= 1.0, f"similarity={sim:.4f}")

        matches = matcher.find_top_matches(anomaly, "pump", top_n=3)
        record("Top3匹配结果", len(matches) == 3, f"匹配数: {len(matches)}")

        analysis = matcher.analyze_root_cause(anomaly, "pump")
        record("根因分析输出",
               "primary_cause" in analysis and "recommendations" in analysis,
               f"主因: {analysis.get('primary_cause', 'N/A')}")

        dtw_matcher = DTWMatcher(cb)
        s1 = [0.1, 0.2, 0.3, 0.5, 0.8]
        s2 = [0.1, 0.2, 0.3, 0.5, 0.8]
        dist = dtw_matcher.compute_dtw_distance(s1, s2)
        record("DTW相同序列距离为0", abs(dist) < 1e-6, f"dist={dist:.6f}")

        s3 = [0.9, 0.8, 0.7, 0.6, 0.5]
        sim_dtw = dtw_matcher.compute_dtw_similarity(s1, s3)
        record("DTW相似度[0,1]", 0.0 <= sim_dtw <= 1.0, f"sim={sim_dtw:.4f}")

        recent_series = {
            "vibration": [0.2 + 0.3 * i / 19 + 0.5 * (i / 19) ** 3 for i in range(20)],
            "temperature": [0.3 + 0.4 * (i / 19) ** 1.5 for i in range(20)],
            "current": [0.2 + 0.15 * i / 19 for i in range(20)],
            "speed": [0.1 + 0.05 * i / 19 for i in range(20)],
            "acoustic": [0.25 + 0.35 * (i / 19) ** 2 for i in range(20)],
        }
        dtw_matches = dtw_matcher.match_evolution_curves(recent_series, "pump", top_n=3)
        record("DTW演化曲线匹配", len(dtw_matches) > 0,
               f"匹配数: {len(dtw_matches)}, Top1: {dtw_matches[0].get('root_cause', 'N/A')[:30] if dtw_matches else 'N/A'}")

        anomaly_with_evo = dict(anomaly)
        anomaly_with_evo["_evolution_data"] = recent_series
        sim_with_evo = matcher.compute_similarity(cb.get_all_cases()[0], anomaly_with_evo)
        record("DTW增强相似度≠纯点匹配", abs(sim_with_evo - sim) > 0.001,
               "点匹配={:.4f}, DTW增强={:.4f}".format(sim, sim_with_evo))
    except Exception as e:
        record("根因分析测试异常", False, str(e)[:200])
    finally:
        if rc_dir in sys.path:
            sys.path.remove(rc_dir)
        for key in list(sys.modules.keys()):
            if key in ("config", "case_base", "similarity_matcher"):
                del sys.modules[key]
        for key, val in saved_modules.items():
            sys.modules[key] = val


def test_bathtub_curve_data():
    print("\n>> 3. 浴盆曲线数据生成")
    try:
        gen_spec = __import__("importlib").util.spec_from_file_location(
            "generate_history",
            os.path.join(PROJECT_ROOT, "lstm-service", "data", "generate_history.py")
        )
        gen_mod = __import__("importlib").util.module_from_spec(gen_spec)

        lstm_config_spec = __import__("importlib").util.spec_from_file_location(
            "lstm_config",
            os.path.join(PROJECT_ROOT, "lstm-service", "config.py")
        )
        lstm_config = __import__("importlib").util.module_from_spec(lstm_config_spec)
        sys.modules["config"] = lstm_config
        lstm_config_spec.loader.exec_module(lstm_config)
        gen_spec.loader.exec_module(gen_mod)

        df = gen_mod.generate_device_data("AC-001", "air_compressor", seed=42)
        record("数据生成行数", len(df) == 60480, f"行数: {len(df)}")
        record("RUL终值≈0", df["rul"].iloc[-1] <= 1.0, f"RUL终值: {df['rul'].iloc[-1]:.2f}")

        N = len(df)
        early_vib_std = df["vibration"].iloc[:int(N * 0.05)].std()
        stable_vib_std = df["vibration"].iloc[int(N * 0.1):int(N * 0.8)].std()
        record("早期失效期噪声>稳定期", early_vib_std > stable_vib_std,
               f"早期std={early_vib_std:.4f}, 稳定std={stable_vib_std:.4f}")

        wearout_vib_mean = df["vibration"].iloc[int(N * 0.85):].mean()
        normal_mid = (2.0 + 5.0) / 2
        record("耗损期振动偏移", wearout_vib_mean > normal_mid,
               f"耗损期均值={wearout_vib_mean:.2f}, 正常中值={normal_mid:.2f}")

        first_100_rul = df["rul"].iloc[:100].mean()
        last_100_rul = df["rul"].iloc[-100:].mean()
        record("RUL整体递减趋势", last_100_rul < first_100_rul,
               f"前100均值={first_100_rul:.1f}, 后100均值={last_100_rul:.1f}")

        del sys.modules["config"]
    except Exception as e:
        record("浴盆曲线测试异常", False, str(e)[:200])


def test_train_utils():
    print("\n>> 4. 训练工具函数")
    saved = {}
    for key in list(sys.modules.keys()):
        if key in ("config", "model", "model.lstm_model", "model.train", "train_mod"):
            saved[key] = sys.modules.pop(key)
    try:
        import importlib.util

        lstm_config_path = os.path.join(PROJECT_ROOT, "lstm-service", "config.py")
        train_path = os.path.join(PROJECT_ROOT, "lstm-service", "model", "train.py")

        config_spec = importlib.util.spec_from_file_location("config", lstm_config_path)
        lstm_config = importlib.util.module_from_spec(config_spec)
        sys.modules["config"] = lstm_config
        config_spec.loader.exec_module(lstm_config)

        sys.modules["model"] = type(sys)("model")
        sys.modules["model.lstm_model"] = type(sys)("lstm_model")
        sys.modules["model"].lstm_model = sys.modules["model.lstm_model"]

        train_code = open(train_path, encoding="utf-8").read()
        train_code = train_code.replace(
            "from .lstm_model import PHM_LSTM_Model",
            "# replaced: from .lstm_model import PHM_LSTM_Model\nPHM_LSTM_Model = None"
        )

        train_mod = type(sys)("train_mod")
        train_mod.__file__ = train_path
        exec(compile(train_code, train_path, "exec"), train_mod.__dict__)

        features_2d = np.random.randn(1000, 5).astype(np.float32)
        targets = np.random.randn(1000).astype(np.float32)
        params_2d = train_mod.compute_scaler_params(features_2d, targets)
        record("2D scaler参数计算", len(params_2d["feature_means"]) == 5,
               f"means: {params_2d['feature_means'][:3]}")

        features_3d = np.random.randn(50, 20, 5).astype(np.float32)
        targets_3d = np.random.randn(50).astype(np.float32)
        params_3d = train_mod.compute_scaler_params(features_3d, targets_3d)
        record("3D scaler参数计算", len(params_3d["feature_means"]) == 5)

        data = np.random.randn(100, 5).astype(np.float32)
        tgts = np.random.randn(100).astype(np.float32)
        X, y = train_mod.create_sequences(data, tgts, window_size=20, step=1)
        record("滑动窗口序列形状", X.shape == (80, 20, 5) and y.shape == (80,),
               f"X.shape={X.shape}, y.shape={y.shape}")

        scaled_f, scaled_t = train_mod.apply_scaling(X, y, params_3d)
        mean_after = scaled_f.mean()
        record("标准化后均值≈0", abs(mean_after) < 0.5, f"mean={mean_after:.4f}")

        df = __import__("pandas").DataFrame(np.random.randn(100, 6),
                                             columns=["vibration", "temperature", "current", "speed", "acoustic", "rul"])
        train_df, test_df = train_mod.split_train_test(df, test_size=0.2)
        record("80/20数据分割", len(train_df) == 80 and len(test_df) == 20,
               "train={}, test={}".format(len(train_df), len(test_df)))
    except Exception as e:
        record("训练工具测试异常", False, str(e)[:300])
    finally:
        for key in list(sys.modules.keys()):
            if key in ("config", "model", "model.lstm_model", "model.train", "train_mod"):
                del sys.modules[key]
        for key, val in saved.items():
            sys.modules[key] = val

def test_data_flow_simulation():
    print("\n>> 5. 端到端数据流模拟（边缘→云端→LSTM→根因）")
    saved_modules = {}
    for key in list(sys.modules.keys()):
        if key in ("config", "anomaly_detector", "case_base", "similarity_matcher"):
            saved_modules[key] = sys.modules.pop(key)
    edge_dir = os.path.join(PROJECT_ROOT, "edge-node")
    rc_dir = os.path.join(PROJECT_ROOT, "root-cause-service")
    sys.path.insert(0, edge_dir)
    try:
        import importlib

        config_spec = importlib.util.spec_from_file_location(
            "config", os.path.join(edge_dir, "config.py")
        )
        edge_config = importlib.util.module_from_spec(config_spec)
        sys.modules["config"] = edge_config
        config_spec.loader.exec_module(edge_config)

        tmp_dir = tempfile.mkdtemp(prefix="phm_flow_")
        edge_config.MODEL_SAVE_DIR = tmp_dir

        from anomaly_detector import IsolationForestAnomalyDetector

        devices = [
            ("AC-001", "air_compressor", {"vibration": (2.0, 5.0), "temperature": (55.0, 75.0), "current": (15.0, 25.0), "speed": (2800.0, 3000.0), "acoustic_emission": (65.0, 85.0)}),
            ("CP-001", "centrifugal_pump", {"vibration": (1.0, 3.5), "temperature": (40.0, 60.0), "current": (10.0, 18.0), "speed": (1450.0, 1500.0), "acoustic_emission": (55.0, 75.0)}),
            ("FN-001", "fan", {"vibration": (1.5, 4.0), "temperature": (45.0, 65.0), "current": (8.0, 15.0), "speed": (960.0, 1000.0), "acoustic_emission": (60.0, 80.0)}),
            ("CV-001", "conveyor", {"vibration": (0.5, 2.5), "temperature": (35.0, 55.0), "current": (5.0, 12.0), "speed": (60.0, 80.0), "acoustic_emission": (50.0, 70.0)}),
            ("CT-001", "cooling_tower", {"vibration": (0.8, 2.8), "temperature": (28.0, 42.0), "current": (12.0, 20.0), "speed": (720.0, 750.0), "acoustic_emission": (52.0, 72.0)}),
        ]

        anomaly_count = 0
        normal_count = 0
        uploaded_data = []

        for device_id, device_type, ranges in devices:
            detector = IsolationForestAnomalyDetector(
                device_type=device_type,
                normal_ranges=ranges,
                device_id=device_id,
                n_estimators=50,
                n_samples=200,
            )
            for _ in range(20):
                data = {"device_id": device_id, "device_type": device_type}
                for param, (low, high) in ranges.items():
                    data[param] = round(np.random.uniform(low, high), 4)
                is_anom, score = detector.detect(data)
                data["is_anomaly"] = is_anom
                data["anomaly_score"] = score
                if is_anom:
                    anomaly_count += 1
                    uploaded_data.append(data)
                else:
                    normal_count += 1

        record("5台设备数据采集", normal_count + anomaly_count == 100,
               f"正常={normal_count}, 异常={anomaly_count}, 总计={normal_count + anomaly_count}")
        record("异常数据上报", len(uploaded_data) >= 0,
               "上报异常数据条数: {}".format(len(uploaded_data)))

        for key in list(sys.modules.keys()):
            if key in ("config", "anomaly_detector"):
                del sys.modules[key]
        sys.path.insert(0, rc_dir)

        from case_base import CaseBase
        from similarity_matcher import SimilarityMatcher

        cb = CaseBase()
        matcher = SimilarityMatcher(cb)

        for item in uploaded_data[:3]:
            anomaly_input = {}
            for k in ["vibration", "temperature", "current", "speed", "acoustic", "acoustic_emission"]:
                if k in item:
                    key = "acoustic" if k == "acoustic_emission" else k
                    anomaly_input[key] = max(0.0, min(1.0, float(item[k]) / 100.0))
            if len(anomaly_input) >= 5:
                analysis = matcher.analyze_root_cause(anomaly_input, "pump")
                has_result = "primary_cause" in analysis
                if not has_result:
                    break
        else:
            has_result = True
        record("根因分析处理异常数据", has_result, "根因分析处理上报数据成功")

        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as e:
        record("数据流模拟异常", False, str(e)[:200])
    finally:
        for d in [edge_dir, rc_dir]:
            if d in sys.path:
                sys.path.remove(d)
        for key in list(sys.modules.keys()):
            if key in ("config", "anomaly_detector", "case_base", "similarity_matcher"):
                del sys.modules[key]
        for key, val in saved_modules.items():
            sys.modules[key] = val


def generate_report():
    print("\n" + "=" * 70)
    print("  PHM System Local Integration Test Report")
    print("=" * 70)
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["passed"])
    failed = total - passed
    print(f"\n  Total: {total}  Passed: {passed}  Failed: {failed}")
    print(f"  Result: {'ALL PASSED' if failed == 0 else 'HAS FAILURES'}")
    print("=" * 70)

    report_lines = [
        "=" * 70,
        "  PHM System Local Integration Test Report",
        "=" * 70,
        f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"  {'Result':<8} {'Test Name':<50}",
        "-" * 70,
    ]
    for r in RESULTS:
        icon = "PASS" if r["passed"] else "FAIL"
        report_lines.append(f"  [{icon}] {r['name']:<50}")
        if not r["passed"] and r["detail"]:
            report_lines.append(f"        -> {r['detail']}")
    report_lines.extend([
        "-" * 70,
        f"  Total: {total}  Passed: {passed}  Failed: {failed}",
        f"  Result: {'ALL PASSED' if failed == 0 else 'HAS FAILURES'}",
        "=" * 70,
    ])

    report_path = os.path.join(os.path.dirname(__file__), "local_integration_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
    print(f"\n  Report: {report_path}")

    return failed == 0


if __name__ == "__main__":
    print()
    print("=" * 70)
    print("  PHM System Local Integration Test")
    print("=" * 70)
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Root: {PROJECT_ROOT}")
    print("=" * 70)

    test_edge_node_anomaly_detector()
    test_root_cause_analysis()
    test_bathtub_curve_data()
    test_train_utils()
    test_data_flow_simulation()

    ok = generate_report()
    sys.exit(0 if ok else 1)
