"""
Main entry point for HealthTek Clinical Data Ingestion pipeline.

Configures logging and executes the data pipeline orchestrator.
"""

import argparse
import logging
import sys
from datetime import datetime

from config import config
from orchestrator import PipelineError, SimpleOrchestrator


def setup_logging(log_level: str = None) -> None:
    """
    Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level = log_level or config.LOG_LEVEL

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=config.LOG_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("pipeline.log", mode="a")],
    )

    logger = logging.getLogger("healthtek")
    logger.info(f"Logging initialized at {level} level")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="HealthTek Clinical Data Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process data for years 2022-2024
  python main.py --years 2022 2023 2024

  # Process with custom directories
  python main.py --years 2023 --bronze-dir ./my_bronze --silver-dir ./my_silver

  # Run with debug logging
  python main.py --years 2023 --log-level DEBUG
        """,
    )

    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=[2019, 2020, 2021, 2022, 2023, 2024],
        help="Years to process for IQSS data (default: 2019-2024)",
    )

    parser.add_argument(
        "--bronze-dir",
        type=str,
        default=None,
        help=f"Directory for raw data (default: {config.BRONZE_DIR})",
    )

    parser.add_argument(
        "--silver-dir",
        type=str,
        default=None,
        help=f"Directory for cleaned data (default: {config.SILVER_DIR})",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help=f"Logging level (default: {config.LOG_LEVEL})",
    )

    parser.add_argument("--finess-only", action="store_true", help="Only run FINESS pipeline")

    parser.add_argument("--iqss-only", action="store_true", help="Only run IQSS pipeline")

    return parser.parse_args()


def main() -> int:
    """
    Main execution function.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    args = parse_arguments()

    # Setup logging
    setup_logging(args.log_level)
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # Reduce noise
    logger = logging.getLogger("healthtek.main")

    print("\n🏥  HealthTek Clinical Data Ingestion Pipeline  🏥")
    print("=" * 60)
    print(f"📅  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂  Bronze Dir: {args.bronze_dir or config.BRONZE_DIR}")
    print(f"📂  Silver Dir: {args.silver_dir or config.SILVER_DIR}")
    print(f"📅  Years: {args.years}")
    print("=" * 60 + "\n")

    start_time = datetime.now()

    try:
        # Initialize orchestrator
        pipeline = SimpleOrchestrator(bronze_dir=args.bronze_dir, silver_dir=args.silver_dir)

        # Run pipeline based on arguments
        if args.finess_only:
            logger.info("🚀  Running FINESS pipeline only...")
            pipeline.run_finess()
        elif args.iqss_only:
            logger.info("🚀  Running IQSS pipeline only...")
            pipeline.run_iqss(args.years)
        else:
            logger.info("🚀  Running full pipeline (FINESS + IQSS)...")
            pipeline.run(args.years)

        duration = datetime.now() - start_time
        print("\n" + "=" * 60)
        print("✅  Pipeline execution completed successfully")
        print(f"⏱️   Total duration: {duration}")
        print("=" * 60 + "\n")

        return 0

    except PipelineError as e:
        print("\n" + "=" * 60)
        print(f"❌  Pipeline failed: {e}")
        print("=" * 60 + "\n")
        logger.error(f"Pipeline failed: {e}")
        return 1

    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
        return 130

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌  Unexpected error: {e}")
        print("=" * 60 + "\n")
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
