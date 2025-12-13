#!/usr/bin/env python3
"""Converts a Hugging Face transformer model to the ONNX format.

This script provides a command-line interface for converting a specified
Hugging Face model to ONNX, which can provide significant performance
improvements for inference. It supports graph optimization and INT8 dynamic
quantization for reduced model size and faster CPU inference.

Usage:
    # Basic export
    python scripts/ops/convert_to_onnx.py --model-name distilbert-base-uncased-finetuned-sst-2-english

    # Export with INT8 quantization (recommended for production)
    python scripts/ops/convert_to_onnx.py --quantize

    # Quantize existing ONNX model
    python scripts/ops/convert_to_onnx.py --quantize-only --input-model ./onnx_models/model.onnx
"""

import argparse
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.onnx_sentiment import ONNXModelOptimizer

logger = get_logger(__name__)


def main():
    """Parses command-line arguments and runs the ONNX conversion process."""
    parser = argparse.ArgumentParser(
        description="Convert Hugging Face models to ONNX format with optional INT8 quantization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert model to ONNX with optimization
  python scripts/ops/convert_to_onnx.py --model-name distilbert-base-uncased-finetuned-sst-2-english

  # Convert with INT8 quantization (4x smaller, 2-3x faster on CPU)
  python scripts/ops/convert_to_onnx.py --quantize

  # Quantize an existing ONNX model
  python scripts/ops/convert_to_onnx.py --quantize-only --input-model ./onnx_models/model.onnx
        """,
    )
    parser.add_argument(
        "--model-name",
        type=str,
        help="Hugging Face model name (default: from config)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./onnx_models",
        help="Output directory for ONNX models (default: ./onnx_models)",
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Skip ONNX graph optimizations",
    )
    parser.add_argument(
        "--quantize",
        action="store_true",
        help="Apply INT8 dynamic quantization (reduces size ~4x, speeds up CPU inference 2-3x)",
    )
    parser.add_argument(
        "--quantize-only",
        action="store_true",
        help="Only quantize an existing ONNX model (requires --input-model)",
    )
    parser.add_argument(
        "--input-model",
        type=str,
        help="Path to existing ONNX model file (for --quantize-only)",
    )
    parser.add_argument(
        "--opset-version",
        type=int,
        default=14,
        help="ONNX opset version (default: 14)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.quantize_only and not args.input_model:
        parser.error("--quantize-only requires --input-model")

    # Handle quantize-only mode
    if args.quantize_only:
        return quantize_existing_model(args.input_model, args.output_dir)

    # Get settings
    settings = get_settings()
    model_name = args.model_name or settings.model.model_name

    logger.info(
        "Starting ONNX conversion",
        model_name=model_name,
        output_dir=args.output_dir,
        optimize=not args.no_optimize,
        quantize=args.quantize,
    )

    try:
        # Export model using static methods
        final_model_path = ONNXModelOptimizer.export_model(
            model_name=model_name,
            output_path=args.output_dir,
            opset_version=args.opset_version,
            quantize=args.quantize,
            optimize_graph=not args.no_optimize,
        )

        print("\n✓ Model successfully converted to ONNX format")
        print(f"  Model: {model_name}")
        print(f"  Output: {final_model_path}")

        # Print model sizes
        output_dir = Path(args.output_dir)
        print("\n  Model files:")
        for onnx_file in sorted(output_dir.glob("*.onnx")):
            size_mb = onnx_file.stat().st_size / (1024 * 1024)
            marker = " ← recommended" if "quantized" in onnx_file.name else ""
            print(f"    {onnx_file.name}: {size_mb:.2f} MB{marker}")

        if args.quantize:
            print("\n  INT8 quantization applied:")
            print("    • ~4x smaller model size")
            print("    • 2-3x faster CPU inference")
            print("    • Negligible accuracy loss")

        return 0

    except Exception as e:
        logger.error("ONNX conversion failed", error=str(e), error_type=type(e).__name__)
        print(f"\n✗ Conversion failed: {e}", file=sys.stderr)
        return 1


def quantize_existing_model(input_model: str, output_dir: str) -> int:
    """Quantize an existing ONNX model.

    Args:
        input_model: Path to the input ONNX model file.
        output_dir: Directory to save the quantized model.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    input_path = Path(input_model)
    if not input_path.exists():
        print(f"✗ Input model not found: {input_model}", file=sys.stderr)
        return 1

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    quantized_path = output_path / "model_quantized.onnx"

    logger.info(
        "Quantizing existing ONNX model",
        input_model=input_model,
        output_path=str(quantized_path),
    )

    try:
        metrics = ONNXModelOptimizer.quantize_model(
            input_path=str(input_path),
            output_path=str(quantized_path),
        )

        print("\n✓ Model successfully quantized")
        print(f"  Input: {input_model}")
        print(f"  Output: {quantized_path}")
        print(f"\n  Original size: {metrics['original_size_mb']:.2f} MB")
        print(f"  Quantized size: {metrics['quantized_size_mb']:.2f} MB")
        print(f"  Size reduction: {metrics['size_reduction_pct']:.1f}%")

        return 0

    except Exception as e:
        logger.error("Quantization failed", error=str(e), error_type=type(e).__name__)
        print(f"\n✗ Quantization failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
