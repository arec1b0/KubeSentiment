from __future__ import annotations

from pathlib import Path

import pytest


def test_quantize_model_targets_linear_ops_and_validates_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pytest.importorskip("onnxruntime")

    import onnxruntime.quantization as ortq  # noqa: PLC0415

    import app.models.onnx_sentiment as onnx_mod  # noqa: PLC0415
    from app.models.onnx_sentiment import ONNXModelOptimizer  # noqa: PLC0415

    input_path = tmp_path / "model.onnx"
    output_path = tmp_path / "model.quantized.onnx"

    # Dummy input model bytes (not a real ONNX graph).
    input_path.write_bytes(b"dummy-onnx")

    calls: dict[str, object] = {}

    def fake_quantize_dynamic(
        in_path: str,
        out_path: str,
        weight_type=None,
        op_types_to_quantize=None,
        extra_options=None,
        **kwargs,
    ) -> None:
        calls["in_path"] = in_path
        calls["out_path"] = out_path
        calls["weight_type"] = weight_type
        calls["op_types_to_quantize"] = op_types_to_quantize
        calls["extra_options"] = extra_options
        Path(out_path).write_bytes(b"quantized")

    monkeypatch.setattr(ortq, "quantize_dynamic", fake_quantize_dynamic)

    # Patch session creation to avoid needing a real ONNX file
    created_sessions: list[str] = []

    def fake_inference_session(model_path: str, *args, **kwargs):
        created_sessions.append(model_path)
        return object()

    monkeypatch.setattr(onnx_mod.ort, "InferenceSession", fake_inference_session)

    metrics = ONNXModelOptimizer.quantize_model(
        input_path=str(input_path),
        output_path=str(output_path),
        op_types_to_quantize=["MatMul", "Gemm"],
        validate_session=True,
    )

    assert output_path.exists()
    assert calls["in_path"] == str(input_path)
    assert calls["out_path"] == str(output_path)
    assert calls["op_types_to_quantize"] == ["MatMul", "Gemm"]
    assert calls["extra_options"] == {"MatMulConstBOnly": True}

    # Validation should create a CPU session for the quantized model
    assert created_sessions == [str(output_path)]

    assert metrics["original_size_mb"] > 0
    assert metrics["quantized_size_mb"] > 0
    assert metrics["quantized_size_mb"] > 0
