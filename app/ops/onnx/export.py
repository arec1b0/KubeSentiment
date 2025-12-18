"""
ONNX Model Export and Optimization Utilities.

This module isolates the build-time dependencies for converting, optimizing,
and quantizing PyTorch models to ONNX format. It prevents heavy libraries
(torch, transformers) from being loaded in the inference runtime.

Dependencies:
    - onnxruntime (required for optimization/quantization)
    - torch (optional, required for export)
    - transformers (optional, required for export)

To use export features, ensure 'torch' and 'transformers' are installed.
"""

from pathlib import Path
from typing import Any

import onnxruntime as ort

from app.core.logging import get_logger

logger = get_logger(__name__)


class ONNXModelOptimizer:
    """Utility class for converting PyTorch models to ONNX format.

    This class provides methods to export trained PyTorch models to ONNX
    format for optimized inference, with optional INT8 quantization.
    """

    @staticmethod
    def export_model(
        model_name: str,
        output_path: str,
        opset_version: int = 14,
        quantize: bool = False,
        optimize_graph: bool = True,
    ) -> str:
        """Export a Hugging Face model to ONNX format.

        Args:
            model_name: The Hugging Face model identifier.
            output_path: Directory path where the ONNX model will be saved.
            opset_version: ONNX opset version to use (default: 14).
            quantize: Whether to apply INT8 dynamic quantization (default: False).
            optimize_graph: Whether to apply graph optimizations (default: True).

        Returns:
            Path to the final ONNX model file.

        Raises:
            RuntimeError: If export fails.
            ImportError: If required dependencies (torch, transformers) are missing.
        """
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as e:
            logger.error("Missing dependencies for model export", error=str(e))
            raise ImportError(
                "PyTorch and Transformers are required for model export. "
                "Please install them with: pip install torch transformers"
            ) from e

        try:
            logger.info(
                "Exporting model to ONNX format",
                model_name=model_name,
                quantize=quantize,
                optimize_graph=optimize_graph,
            )

            # Load model and tokenizer (use FastTokenizer for better performance)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)

            # Create output directory
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save tokenizer
            tokenizer.save_pretrained(str(output_dir))

            # Create dummy input
            dummy_text = "This is a sample text for export."
            inputs = tokenizer(
                dummy_text,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            # Export to ONNX
            onnx_path = output_dir / "model.onnx"
            torch.onnx.export(
                model,
                (inputs["input_ids"], inputs["attention_mask"]),
                str(onnx_path),
                input_names=["input_ids", "attention_mask"],
                output_names=["logits"],
                dynamic_axes={
                    "input_ids": {0: "batch_size", 1: "sequence_length"},
                    "attention_mask": {0: "batch_size", 1: "sequence_length"},
                    "logits": {0: "batch_size"},
                },
                opset_version=opset_version,
            )

            logger.info("Base ONNX model exported", path=str(onnx_path))
            final_model_path = onnx_path

            # Apply graph optimizations
            if optimize_graph:
                optimized_path = output_dir / "model_optimized.onnx"
                ONNXModelOptimizer.optimize_graph(str(onnx_path), str(optimized_path))
                final_model_path = optimized_path

            # Apply INT8 dynamic quantization (weights-only; no calibration)
            if quantize:
                input_path = final_model_path
                quantized_path = output_dir / "model.quantized.onnx"
                metrics = ONNXModelOptimizer.quantize_model(
                    input_path=str(input_path),
                    output_path=str(quantized_path),
                    op_types_to_quantize=["MatMul", "Gemm"],
                )
                # Backward-compatible artifact name used by older deployments/docs
                legacy_quantized_path = output_dir / "model_quantized.onnx"
                if legacy_quantized_path != quantized_path and not legacy_quantized_path.exists():
                    try:
                        import shutil

                        shutil.copy2(quantized_path, legacy_quantized_path)
                    except Exception as e:
                        # Critical: Dockerfile.optimized and other scripts depend on this specific filename
                        # Invoked by scripts/ops/convert_to_onnx.py and potentially other deployment automation.
                        # Failing here prevents creating a broken image.
                        logger.error(
                            "Failed to create legacy quantized artifact name",
                            legacy_path=str(legacy_quantized_path),
                            primary_path=str(quantized_path),
                            error=str(e),
                        )
                        raise RuntimeError(
                            f"Failed to create legacy artifact {legacy_quantized_path}. "
                            "This file is required by Dockerfile.optimized build process."
                        ) from e

                final_model_path = quantized_path
                logger.info("Quantization metrics", **metrics)

            logger.info("Model export completed", final_path=str(final_model_path))
            return str(final_model_path)

        except Exception as e:
            logger.error("Failed to export model to ONNX", error=str(e))
            raise RuntimeError(f"ONNX export failed: {e}") from e


    @staticmethod
    def optimize_graph(input_path: str, output_path: str) -> None:
        """Apply ONNX Runtime graph optimizations.

        Args:
            input_path: Path to the input ONNX model.
            output_path: Path to save the optimized model.

        Raises:
            RuntimeError: If optimization fails.
        """
        try:
            logger.info("Applying graph optimizations", input_path=input_path)

            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.optimized_model_filepath = output_path

            # Create session to trigger optimization and save
            ort.InferenceSession(input_path, sess_options, providers=["CPUExecutionProvider"])

            logger.info("Graph optimization completed", output_path=output_path)

        except Exception as e:
            logger.error("Graph optimization failed", error=str(e))
            raise RuntimeError(f"Graph optimization failed: {e}") from e

    @staticmethod
    def quantize_model(
        input_path: str,
        output_path: str,
        weight_type: str = "QInt8",
        op_types_to_quantize: list[str] | None = None,
        validate_session: bool = True,
    ) -> dict[str, Any]:
        """Apply INT8 dynamic quantization to an ONNX model.

        Dynamic quantization converts FP32 weights to INT8, reducing model size
        by ~4x and improving CPU inference speed by 2-3x with negligible
        accuracy loss.

        Args:
            input_path: Path to the input ONNX model.
            output_path: Path to save the quantized model.
            weight_type: Quantization type - "QInt8" or "QUInt8" (default: "QInt8").
            op_types_to_quantize: Optional list of op types to quantize. Defaults to
                ["MatMul", "Gemm"] to target transformer linear layers.
            validate_session: If True, validates the resulting model by creating an
                onnxruntime.InferenceSession on CPU.

        Returns:
            Dictionary containing quantization metrics:
                - original_size_mb: Size of original model in MB
                - quantized_size_mb: Size of quantized model in MB
                - size_reduction_pct: Percentage size reduction

        Raises:
            RuntimeError: If quantization fails.
        """
        try:
            import os

            from onnxruntime.quantization import QuantType, quantize_dynamic

            logger.info(
                "Applying INT8 dynamic quantization",
                input_path=input_path,
                weight_type=weight_type,
                op_types_to_quantize=op_types_to_quantize,
            )

            # Map string to QuantType enum
            quant_type_map = {
                "QInt8": QuantType.QInt8,
                "QUInt8": QuantType.QUInt8,
            }
            quant_type = quant_type_map.get(weight_type, QuantType.QInt8)

            # Default: target transformer linear layers
            if op_types_to_quantize is None:
                op_types_to_quantize = ["MatMul", "Gemm"]

            # Apply dynamic quantization (weights only)
            quantize_dynamic(
                input_path,
                output_path,
                weight_type=quant_type,
                op_types_to_quantize=op_types_to_quantize,
                extra_options={"MatMulConstBOnly": True},
            )

            if validate_session:
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                _ = ort.InferenceSession(
                    output_path,
                    sess_options=sess_options,
                    providers=["CPUExecutionProvider"],
                )

            # Calculate size metrics
            original_size = os.path.getsize(input_path)
            quantized_size = os.path.getsize(output_path)
            size_reduction = (1 - quantized_size / original_size) * 100

            metrics = {
                "original_size_mb": original_size / 1024 / 1024,
                "quantized_size_mb": quantized_size / 1024 / 1024,
                "size_reduction_pct": size_reduction,
            }

            logger.info(
                "INT8 quantization completed",
                original_size_mb=metrics['original_size_mb'],
                quantized_size_mb=metrics['quantized_size_mb'],
                size_reduction_pct=metrics['size_reduction_pct'],
            )

            return metrics

        except ImportError as e:
            logger.error(
                "onnxruntime.quantization not available",
                error=str(e),
                hint="Install with: pip install onnxruntime",
            )
            raise RuntimeError(
                "onnxruntime.quantization module not available. "
                "Install onnxruntime with: pip install onnxruntime"
            ) from e
        except Exception as e:
            logger.error("INT8 quantization failed", error=str(e))
            raise RuntimeError(f"INT8 quantization failed: {e}") from e
