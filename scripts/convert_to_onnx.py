#!/usr/bin/env python3
"""Converts a Hugging Face transformer model to the ONNX format.

This script provides a command-line interface for converting a specified
Hugging Face model to ONNX, which can provide significant performance
improvements for inference. It allows for optimizations and quantization to be
applied during the conversion process.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.logging_config import get_logger
from app.ml.onnx_optimizer import ONNXModelOptimizer

logger = get_logger(__name__)


def main():
    """Parses command-line arguments and runs the ONNX conversion process."""
    parser = argparse.ArgumentParser(description="Convert Hugging Face models to ONNX format")
    parser.add_argument(
        "--model-name", type=str, help="Hugging Face model name (default: from config)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./onnx_models",
        help="Output directory for ONNX models",
    )
    parser.add_argument(
        "--optimize", action="store_true", default=True, help="Apply ONNX optimizations"
    )
    parser.add_argument(
        "--quantize",
        action="store_true",
        help="Apply quantization for smaller model size",
    )

    args = parser.parse_args()

    # Get settings
    settings = get_settings()
    model_name = args.model_name or settings.model_name

    logger.info(
        "Starting ONNX conversion",
        model_name=model_name,
        output_dir=args.output_dir,
        optimize=args.optimize,
        quantize=args.quantize,
    )

    try:
        # Create optimizer
        optimizer = ONNXModelOptimizer(model_name=model_name, cache_dir=args.output_dir)

        # Convert to ONNX
        onnx_path = optimizer.convert_to_onnx(optimize=args.optimize, quantize=args.quantize)

        logger.info("ONNX conversion successful", onnx_path=str(onnx_path))

        print(f"\n✓ Model successfully converted to ONNX format")
        print(f"  Location: {onnx_path}")
        print(f"  Model: {model_name}")

        # Print model info
        onnx_file = onnx_path / "model.onnx"
        if onnx_file.exists():
            size_mb = onnx_file.stat().st_size / (1024 * 1024)
            print(f"  Size: {size_mb:.2f} MB")

        return 0

    except Exception as e:
        logger.error("ONNX conversion failed", error=str(e), error_type=type(e).__name__)
        print(f"\n✗ Conversion failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
