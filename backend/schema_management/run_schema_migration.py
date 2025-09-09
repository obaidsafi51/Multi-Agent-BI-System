#!/usr/bin/env python3
"""
Schema Migration Runner.

This script executes the complete schema migration implementation:
- Performance Optimization and Tuning
- Static Dependency Removal and Final Migration
- Validation and Rollback Procedures

Usage:
    python run_schema_migration.py [--dry-run] [--optimization-level LEVEL] [--enable-benchmarks] [--backup-dir DIR]
"""

import asyncio
import argparse
import logging
import sys
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent
sys.path.append(str(backend_path))

from schema_management.schema_migration_orchestrator import (
    SchemaMigrationOrchestrator, run_schema_migration
)
from schema_management.performance_optimizer import OptimizationLevel

# Configure logging
def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                f"schema_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
        ]
    )

logger = logging.getLogger(__name__)


def print_banner():
    """Print Phase 5 implementation banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                                                                              ║
    ║                    🚀 PHASE 5 IMPLEMENTATION 🚀                            ║
    ║                                                                              ║
    ║              Performance Optimization & Final Migration                      ║
    ║                     Dynamic Schema Management                                ║
    ║                                                                              ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def run_dry_run_analysis(project_root: str) -> dict:
    """Run dry-run analysis to preview changes."""
    logger.info("🔍 Running dry-run analysis...")
    
    try:
        from schema_management.static_dependency_removal import StaticDependencyScanner
        
        # Scan for dependencies
        scanner = StaticDependencyScanner(project_root)
        dependencies = await scanner.scan_project()
        
        # Generate report
        report = scanner.generate_migration_report()
        
        # Preview changes
        preview = {
            "dependencies_found": len(dependencies),
            "files_affected": report["files_affected"],
            "by_severity": report["summary"],
            "by_type": report["by_type"],
            "top_affected_files": report["most_affected_files"][:5],
            "migration_priority": report["migration_priority"][:10]
        }
        
        return preview
        
    except Exception as e:
        logger.error(f"Dry-run analysis failed: {e}")
        return {"error": str(e)}


def print_dry_run_summary(preview: dict):
    """Print dry-run summary."""
    if "error" in preview:
        print(f"❌ Dry-run analysis failed: {preview['error']}")
        return
    
    print("\n📊 DRY-RUN ANALYSIS SUMMARY")
    print("=" * 50)
    
    print(f"📁 Files affected: {preview['files_affected']}")
    print(f"🔗 Total dependencies: {preview['dependencies_found']}")
    
    print("\n📈 By Severity:")
    severity = preview["by_severity"]
    for level in ["critical", "high", "medium", "low"]:
        count = severity.get(level, 0)
        if count > 0:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[level]
            print(f"  {icon} {level.title()}: {count}")
    
    print("\n📝 By Type:")
    for dep_type, count in preview["by_type"].items():
        print(f"  • {dep_type}: {count}")
    
    if preview["top_affected_files"]:
        print("\n📂 Most Affected Files:")
        for file_path, count in preview["top_affected_files"]:
            print(f"  • {Path(file_path).name}: {count} dependencies")
    
    print("\n🎯 Top Priority Items:")
    for i, item in enumerate(preview["migration_priority"][:5], 1):
        severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        icon = severity_icon.get(item["severity"], "⚪")
        print(f"  {i}. {icon} {Path(item['file']).name}:{item['line']} - {item['type']}")


async def confirm_execution() -> bool:
    """Ask user to confirm execution."""
    while True:
        response = input("\n❓ Do you want to proceed with Phase 5 implementation? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Phase 5 Implementation - Performance Optimization and Final Migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_schema_migration.py --dry-run                    # Preview changes only
  python run_schema_migration.py --optimization-level basic   # Run with basic optimization
  python run_schema_migration.py --enable-benchmarks          # Include performance benchmarks
  python run_schema_migration.py --backup-dir ./my_backups    # Use custom backup directory
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing them"
    )
    
    parser.add_argument(
        "--optimization-level",
        choices=["basic", "intermediate", "aggressive"],
        default="intermediate",
        help="Performance optimization level (default: intermediate)"
    )
    
    parser.add_argument(
        "--enable-benchmarks",
        action="store_true",
        help="Run performance benchmarks (may take longer)"
    )
    
    parser.add_argument(
        "--backup-dir",
        type=str,
        help="Directory for backup files (default: ./migration_backups)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory parent)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Print banner
    print_banner()
    
    # Determine project root
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        project_root = Path(__file__).parent.parent.parent.resolve()
    
    logger.info(f"Project root: {project_root}")
    
    # Validate project root
    if not project_root.exists():
        logger.error(f"Project root does not exist: {project_root}")
        sys.exit(1)
    
    # Convert optimization level
    optimization_mapping = {
        "basic": OptimizationLevel.BASIC,
        "intermediate": OptimizationLevel.INTERMEDIATE,
        "aggressive": OptimizationLevel.AGGRESSIVE
    }
    optimization_level = optimization_mapping[args.optimization_level]
    
    try:
        # Always run dry-run analysis first
        logger.info("Starting Phase 5 implementation analysis...")
        preview = await run_dry_run_analysis(str(project_root))
        print_dry_run_summary(preview)
        
        if args.dry_run:
            logger.info("✅ Dry-run analysis completed. Use --no-dry-run to execute changes.")
            sys.exit(0)
        
        # Ask for confirmation unless forced
        if not args.force:
            if not await confirm_execution():
                logger.info("👋 Phase 5 implementation cancelled by user.")
                sys.exit(0)
        
        # Run Phase 5 implementation
        logger.info("🚀 Starting schema migration implementation...")
        
        results = await run_schema_migration(
            project_root=str(project_root),
            optimization_level=optimization_level,
            enable_benchmarking=args.enable_benchmarks,
            backup_directory=args.backup_dir
        )
        
        # Save results
        results_file = project_root / f"schema_migration_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📄 Results saved to: {results_file}")
        
        # Create schema migration orchestrator instance for report generation
        orchestrator = SchemaMigrationOrchestrator(
            project_root=str(project_root),
            optimization_level=optimization_level,
            enable_benchmarking=args.enable_benchmarks,
            backup_directory=args.backup_dir
        )
        orchestrator.implementation_results = results
        
        # Generate implementation report
        report = orchestrator.generate_implementation_report()
        report_file = project_root / f"schema_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"📋 Implementation report saved to: {report_file}")
        
        # Create rollback plan
        rollback_plan = await orchestrator.create_rollback_plan()
        logger.info("📋 Rollback plan created")
        
        # Print summary
        success = results.get("success", False)
        if success:
            print("\n🎉 PHASE 5 IMPLEMENTATION COMPLETED SUCCESSFULLY!")
            print("✅ Performance optimization applied")
            print("✅ Static dependencies migrated")
            print("✅ System validation passed")
            print(f"📄 Full report: {report_file}")
        else:
            print("\n❌ PHASE 5 IMPLEMENTATION FAILED")
            errors = results.get("errors", [])
            if errors:
                print("🚨 Errors encountered:")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"  • {error}")
            print(f"📄 Error details: {results_file}")
        
        # Show key recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            print("\n💡 KEY RECOMMENDATIONS:")
            for rec in recommendations[:3]:  # Show top 3 recommendations
                print(f"  • {rec}")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Phase 5 implementation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Phase 5 implementation failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
