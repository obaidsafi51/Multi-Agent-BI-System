"""
Comprehensive validation result reporting system.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import asdict

from .models import ValidationResult, ValidationError, ValidationWarning, ValidationSeverity

logger = logging.getLogger(__name__)


class ValidationReporter:
    """
    Comprehensive validation result reporting system.
    
    Provides detailed reporting, formatting, and analysis of validation results
    for monitoring, debugging, and compliance purposes.
    """
    
    def __init__(self):
        """Initialize validation reporter."""
        self.report_history: List[Dict[str, Any]] = []
        logger.info("Initialized Validation Reporter")
    
    def generate_detailed_report(
        self,
        validation_result: ValidationResult,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a detailed validation report.
        
        Args:
            validation_result: Validation result to report on
            context: Additional context information (database, table, etc.)
            
        Returns:
            Detailed validation report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "validation_summary": {
                "is_valid": validation_result.is_valid,
                "total_errors": len(validation_result.errors),
                "total_warnings": len(validation_result.warnings),
                "validated_fields_count": len(validation_result.validated_fields),
                "validation_time_ms": validation_result.validation_time_ms
            },
            "context": context or {},
            "errors": self._format_errors(validation_result.errors),
            "warnings": self._format_warnings(validation_result.warnings),
            "validated_fields": validation_result.validated_fields,
            "performance_metrics": {
                "validation_time_ms": validation_result.validation_time_ms,
                "performance_rating": self._get_performance_rating(validation_result.validation_time_ms),
                "efficiency_score": self._calculate_efficiency_score(validation_result)
            },
            "recommendations": self._generate_recommendations(validation_result)
        }
        
        # Add to history
        self.report_history.append(report)
        
        # Keep only last 100 reports in memory
        if len(self.report_history) > 100:
            self.report_history = self.report_history[-100:]
        
        return report
    
    def _format_errors(self, errors: List[ValidationError]) -> List[Dict[str, Any]]:
        """Format validation errors for reporting."""
        formatted_errors = []
        
        for error in errors:
            formatted_error = {
                "field": error.field,
                "message": error.message,
                "severity": error.severity.value,
                "error_code": error.error_code,
                "suggested_value": error.suggested_value,
                "category": self._categorize_error(error)
            }
            formatted_errors.append(formatted_error)
        
        return formatted_errors
    
    def _format_warnings(self, warnings: List[ValidationWarning]) -> List[Dict[str, Any]]:
        """Format validation warnings for reporting."""
        formatted_warnings = []
        
        for warning in warnings:
            formatted_warning = {
                "field": warning.field,
                "message": warning.message,
                "suggestion": warning.suggestion,
                "category": self._categorize_warning(warning)
            }
            formatted_warnings.append(formatted_warning)
        
        return formatted_warnings
    
    def _categorize_error(self, error: ValidationError) -> str:
        """Categorize validation error for better organization."""
        if error.error_code:
            if "TYPE" in error.error_code:
                return "data_type"
            elif "NULL" in error.error_code:
                return "null_constraint"
            elif "PRIMARY_KEY" in error.error_code:
                return "primary_key"
            elif "FOREIGN_KEY" in error.error_code:
                return "foreign_key"
            elif "UNIQUE" in error.error_code:
                return "unique_constraint"
            elif "LENGTH" in error.error_code or "SIZE" in error.error_code:
                return "size_constraint"
            elif "RANGE" in error.error_code:
                return "range_constraint"
            elif "FORMAT" in error.error_code:
                return "format_validation"
            elif "SCHEMA" in error.error_code:
                return "schema_validation"
            elif "SYSTEM" in error.error_code:
                return "system_error"
        
        return "general"
    
    def _categorize_warning(self, warning: ValidationWarning) -> str:
        """Categorize validation warning for better organization."""
        message_lower = warning.message.lower()
        
        if "performance" in message_lower or "time" in message_lower:
            return "performance"
        elif "unusual" in message_lower or "unexpected" in message_lower:
            return "data_quality"
        elif "fallback" in message_lower or "unavailable" in message_lower:
            return "system_fallback"
        elif "foreign key" in message_lower:
            return "relationship"
        elif "percentage" in message_lower or "margin" in message_lower:
            return "financial_metrics"
        
        return "general"
    
    def _get_performance_rating(self, validation_time_ms: int) -> str:
        """Get performance rating based on validation time."""
        if validation_time_ms < 100:
            return "excellent"
        elif validation_time_ms < 500:
            return "good"
        elif validation_time_ms < 1000:
            return "fair"
        elif validation_time_ms < 5000:
            return "poor"
        else:
            return "very_poor"
    
    def _calculate_efficiency_score(self, validation_result: ValidationResult) -> float:
        """Calculate efficiency score based on validation metrics."""
        # Base score
        score = 100.0
        
        # Deduct points for errors (more severe deduction)
        score -= len(validation_result.errors) * 10
        
        # Deduct points for warnings (less severe deduction)
        score -= len(validation_result.warnings) * 2
        
        # Deduct points for slow validation
        if validation_result.validation_time_ms > 1000:
            score -= (validation_result.validation_time_ms - 1000) / 100
        
        # Bonus points for validating many fields quickly
        if validation_result.validation_time_ms < 500 and len(validation_result.validated_fields) > 5:
            score += 5
        
        return max(0.0, min(100.0, score))
    
    def _generate_recommendations(self, validation_result: ValidationResult) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Performance recommendations
        if validation_result.validation_time_ms > 2000:
            recommendations.append("Consider enabling schema caching to improve validation performance")
        
        # Error pattern recommendations
        error_categories = {}
        for error in validation_result.errors:
            category = self._categorize_error(error)
            error_categories[category] = error_categories.get(category, 0) + 1
        
        if error_categories.get("data_type", 0) > 2:
            recommendations.append("Multiple data type errors detected - review data input validation")
        
        if error_categories.get("null_constraint", 0) > 1:
            recommendations.append("Multiple null constraint violations - ensure required fields are populated")
        
        if error_categories.get("size_constraint", 0) > 1:
            recommendations.append("Multiple size constraint violations - review data truncation or field sizing")
        
        # Warning pattern recommendations
        warning_categories = {}
        for warning in validation_result.warnings:
            category = self._categorize_warning(warning)
            warning_categories[category] = warning_categories.get(category, 0) + 1
        
        if warning_categories.get("system_fallback", 0) > 0:
            recommendations.append("System fallback detected - check MCP server connectivity and configuration")
        
        if warning_categories.get("financial_metrics", 0) > 1:
            recommendations.append("Multiple financial metric warnings - review calculation logic and data accuracy")
        
        # General recommendations
        if not validation_result.is_valid and len(validation_result.errors) > 5:
            recommendations.append("High error count detected - consider implementing data quality checks upstream")
        
        if len(validation_result.warnings) > 10:
            recommendations.append("High warning count - review validation thresholds and data quality processes")
        
        return recommendations
    
    def generate_summary_report(
        self,
        validation_results: List[ValidationResult],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary report for multiple validation results.
        
        Args:
            validation_results: List of validation results to summarize
            context: Additional context information
            
        Returns:
            Summary validation report
        """
        if not validation_results:
            return {
                "timestamp": datetime.now().isoformat(),
                "context": context or {},
                "summary": "No validation results to report",
                "total_validations": 0
            }
        
        total_validations = len(validation_results)
        successful_validations = sum(1 for result in validation_results if result.is_valid)
        total_errors = sum(len(result.errors) for result in validation_results)
        total_warnings = sum(len(result.warnings) for result in validation_results)
        total_fields = sum(len(result.validated_fields) for result in validation_results)
        total_time_ms = sum(result.validation_time_ms for result in validation_results)
        
        # Calculate averages
        avg_time_ms = total_time_ms / total_validations if total_validations > 0 else 0
        avg_fields_per_validation = total_fields / total_validations if total_validations > 0 else 0
        
        # Error and warning analysis
        error_analysis = self._analyze_error_patterns(validation_results)
        warning_analysis = self._analyze_warning_patterns(validation_results)
        
        summary_report = {
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "summary_metrics": {
                "total_validations": total_validations,
                "successful_validations": successful_validations,
                "success_rate": (successful_validations / total_validations * 100) if total_validations > 0 else 0,
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_validated_fields": total_fields,
                "average_validation_time_ms": round(avg_time_ms, 2),
                "average_fields_per_validation": round(avg_fields_per_validation, 2)
            },
            "performance_analysis": {
                "fastest_validation_ms": min(result.validation_time_ms for result in validation_results),
                "slowest_validation_ms": max(result.validation_time_ms for result in validation_results),
                "performance_distribution": self._get_performance_distribution(validation_results)
            },
            "error_analysis": error_analysis,
            "warning_analysis": warning_analysis,
            "recommendations": self._generate_batch_recommendations(validation_results)
        }
        
        return summary_report
    
    def _analyze_error_patterns(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """Analyze error patterns across multiple validation results."""
        error_categories = {}
        error_fields = {}
        error_codes = {}
        
        for result in validation_results:
            for error in result.errors:
                # Count by category
                category = self._categorize_error(error)
                error_categories[category] = error_categories.get(category, 0) + 1
                
                # Count by field
                error_fields[error.field] = error_fields.get(error.field, 0) + 1
                
                # Count by error code
                if error.error_code:
                    error_codes[error.error_code] = error_codes.get(error.error_code, 0) + 1
        
        return {
            "most_common_categories": sorted(error_categories.items(), key=lambda x: x[1], reverse=True)[:5],
            "most_problematic_fields": sorted(error_fields.items(), key=lambda x: x[1], reverse=True)[:5],
            "most_common_error_codes": sorted(error_codes.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def _analyze_warning_patterns(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """Analyze warning patterns across multiple validation results."""
        warning_categories = {}
        warning_fields = {}
        
        for result in validation_results:
            for warning in result.warnings:
                # Count by category
                category = self._categorize_warning(warning)
                warning_categories[category] = warning_categories.get(category, 0) + 1
                
                # Count by field
                warning_fields[warning.field] = warning_fields.get(warning.field, 0) + 1
        
        return {
            "most_common_categories": sorted(warning_categories.items(), key=lambda x: x[1], reverse=True)[:5],
            "most_warned_fields": sorted(warning_fields.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def _get_performance_distribution(self, validation_results: List[ValidationResult]) -> Dict[str, int]:
        """Get performance distribution across validation results."""
        distribution = {
            "excellent": 0,  # < 100ms
            "good": 0,       # 100-500ms
            "fair": 0,       # 500-1000ms
            "poor": 0,       # 1000-5000ms
            "very_poor": 0   # > 5000ms
        }
        
        for result in validation_results:
            rating = self._get_performance_rating(result.validation_time_ms)
            distribution[rating] += 1
        
        return distribution
    
    def _generate_batch_recommendations(self, validation_results: List[ValidationResult]) -> List[str]:
        """Generate recommendations for batch validation results."""
        recommendations = []
        
        total_validations = len(validation_results)
        successful_validations = sum(1 for result in validation_results if result.is_valid)
        success_rate = (successful_validations / total_validations * 100) if total_validations > 0 else 0
        
        # Success rate recommendations
        if success_rate < 50:
            recommendations.append("Low validation success rate - implement comprehensive data quality checks")
        elif success_rate < 80:
            recommendations.append("Moderate validation success rate - review and improve data input processes")
        
        # Performance recommendations
        avg_time = sum(result.validation_time_ms for result in validation_results) / total_validations
        if avg_time > 1000:
            recommendations.append("High average validation time - optimize schema caching and validation logic")
        
        # Error pattern recommendations
        total_errors = sum(len(result.errors) for result in validation_results)
        if total_errors > total_validations * 2:  # More than 2 errors per validation on average
            recommendations.append("High error density - implement upstream data validation and cleansing")
        
        return recommendations
    
    def export_report_to_json(self, report: Dict[str, Any], filepath: str) -> bool:
        """
        Export validation report to JSON file.
        
        Args:
            report: Validation report to export
            filepath: File path to save the report
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Validation report exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export validation report: {e}")
            return False
    
    def get_report_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent validation report history.
        
        Args:
            limit: Maximum number of reports to return
            
        Returns:
            List of recent validation reports
        """
        return self.report_history[-limit:] if self.report_history else []
    
    def clear_report_history(self):
        """Clear validation report history."""
        self.report_history.clear()
        logger.info("Validation report history cleared")


# Utility functions for report formatting

def format_validation_result_for_display(validation_result: ValidationResult) -> str:
    """
    Format validation result for human-readable display.
    
    Args:
        validation_result: Validation result to format
        
    Returns:
        Formatted string representation
    """
    lines = []
    
    # Header
    status = "✅ VALID" if validation_result.is_valid else "❌ INVALID"
    lines.append(f"Validation Result: {status}")
    lines.append(f"Validation Time: {validation_result.validation_time_ms}ms")
    lines.append(f"Validated Fields: {len(validation_result.validated_fields)}")
    lines.append("")
    
    # Errors
    if validation_result.errors:
        lines.append(f"❌ Errors ({len(validation_result.errors)}):")
        for error in validation_result.errors:
            lines.append(f"  • {error.field}: {error.message}")
            if error.suggested_value:
                lines.append(f"    Suggestion: {error.suggested_value}")
        lines.append("")
    
    # Warnings
    if validation_result.warnings:
        lines.append(f"⚠️  Warnings ({len(validation_result.warnings)}):")
        for warning in validation_result.warnings:
            lines.append(f"  • {warning.field}: {warning.message}")
            if warning.suggestion:
                lines.append(f"    Suggestion: {warning.suggestion}")
        lines.append("")
    
    # Validated fields
    if validation_result.validated_fields:
        lines.append(f"✅ Validated Fields: {', '.join(validation_result.validated_fields)}")
    
    return "\n".join(lines)


def create_validation_reporter() -> ValidationReporter:
    """
    Factory function to create a validation reporter.
    
    Returns:
        ValidationReporter instance
    """
    return ValidationReporter()