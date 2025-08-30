"""
CFO terminology to database schema mapping with semantic relationships.
"""

import json
import os
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher
from pathlib import Path

from ..models.core import FinancialEntity
from .types import TermMapping


class TermMapper:
    """Maps CFO terminology to database schema with semantic relationships"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the term mapper with configuration files"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config")
        
        self.config_path = Path(config_path)
        self.business_terms: Dict[str, Dict] = {}
        self.term_mappings: Dict[str, TermMapping] = {}
        self.synonym_index: Dict[str, str] = {}  # synonym -> canonical term
        self.similarity_threshold = 0.7
        
        self._load_configurations()
        self._build_mappings()
        self._build_synonym_index()
    
    def _load_configurations(self) -> None:
        """Load business terms configuration from JSON files"""
        try:
            business_terms_file = self.config_path / "business_terms.json"
            with open(business_terms_file, 'r') as f:
                config = json.load(f)
                self.business_terms = config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {business_terms_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def _build_mappings(self) -> None:
        """Build term mappings from configuration"""
        # Process financial metrics
        for term, config in self.business_terms.get("financial_metrics", {}).items():
            mapping = TermMapping(
                business_term=term,
                database_mapping=config.get("database_mapping", ""),
                synonyms=config.get("synonyms", []),
                category=config.get("category", "unknown"),
                data_type=config.get("data_type", "decimal"),
                aggregation_methods=config.get("aggregation_methods", ["sum"]),
                description=config.get("description", "")
            )
            self.term_mappings[term] = mapping
        
        # Process departments
        for term, config in self.business_terms.get("departments", {}).items():
            mapping = TermMapping(
                business_term=term,
                database_mapping=config.get("database_mapping", ""),
                synonyms=config.get("synonyms", []),
                category="department",
                data_type="string",
                aggregation_methods=["group_by"],
                description=config.get("description", "")
            )
            self.term_mappings[term] = mapping
    
    def _build_synonym_index(self) -> None:
        """Build index of synonyms to canonical terms"""
        for canonical_term, mapping in self.term_mappings.items():
            # Add the canonical term itself
            self.synonym_index[canonical_term.lower()] = canonical_term
            
            # Add all synonyms
            for synonym in mapping.synonyms:
                self.synonym_index[synonym.lower()] = canonical_term
    
    def map_term(self, term: str) -> Optional[FinancialEntity]:
        """Map a business term to a financial entity with database mapping"""
        term_lower = term.lower().strip()
        
        # Direct match in synonym index
        if term_lower in self.synonym_index:
            canonical_term = self.synonym_index[term_lower]
            mapping = self.term_mappings[canonical_term]
            
            return FinancialEntity(
                entity_type="metric" if mapping.category != "department" else "department",
                entity_value=canonical_term,
                confidence_score=1.0,
                synonyms=mapping.synonyms,
                database_mapping=mapping.database_mapping
            )
        
        # Fuzzy matching for similar terms
        best_match = self._find_similar_term(term_lower)
        if best_match:
            canonical_term, confidence = best_match
            mapping = self.term_mappings[canonical_term]
            
            return FinancialEntity(
                entity_type="metric" if mapping.category != "department" else "department",
                entity_value=canonical_term,
                confidence_score=confidence,
                synonyms=mapping.synonyms,
                database_mapping=mapping.database_mapping
            )
        
        return None
    
    def _find_similar_term(self, term: str) -> Optional[Tuple[str, float]]:
        """Find the most similar term using fuzzy matching"""
        best_match = None
        best_score = 0.0
        
        # Check against all synonyms and canonical terms
        for synonym, canonical_term in self.synonym_index.items():
            similarity = SequenceMatcher(None, term, synonym).ratio()
            
            if similarity > best_score and similarity >= self.similarity_threshold:
                best_score = similarity
                best_match = (canonical_term, similarity)
        
        return best_match
    
    def get_similar_terms(self, term: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Get a list of similar terms with confidence scores"""
        term_lower = term.lower().strip()
        similarities = []
        
        for synonym, canonical_term in self.synonym_index.items():
            similarity = SequenceMatcher(None, term_lower, synonym).ratio()
            if similarity >= 0.3:  # Lower threshold for suggestions
                similarities.append((canonical_term, similarity))
        
        # Sort by similarity and remove duplicates
        unique_terms = {}
        for canonical_term, similarity in similarities:
            if canonical_term not in unique_terms or similarity > unique_terms[canonical_term]:
                unique_terms[canonical_term] = similarity
        
        sorted_terms = sorted(unique_terms.items(), key=lambda x: x[1], reverse=True)
        return sorted_terms[:limit]
    
    def get_term_mapping(self, term: str) -> Optional[TermMapping]:
        """Get the complete term mapping for a canonical term"""
        return self.term_mappings.get(term)
    
    def get_database_mapping(self, term: str) -> Optional[str]:
        """Get the database mapping for a term"""
        entity = self.map_term(term)
        return entity.database_mapping if entity else None
    
    def get_aggregation_methods(self, term: str) -> List[str]:
        """Get valid aggregation methods for a term"""
        mapping = self.get_term_mapping(term)
        if mapping:
            return mapping.aggregation_methods
        
        # Try to map the term first
        entity = self.map_term(term)
        if entity:
            canonical_mapping = self.get_term_mapping(entity.entity_value)
            return canonical_mapping.aggregation_methods if canonical_mapping else ["sum"]
        
        return ["sum"]  # Default aggregation
    
    def get_terms_by_category(self, category: str) -> List[str]:
        """Get all terms in a specific category"""
        return [
            term for term, mapping in self.term_mappings.items()
            if mapping.category == category
        ]
    
    def validate_term_combination(self, terms: List[str]) -> Dict[str, Any]:
        """Validate if a combination of terms makes sense together"""
        mapped_terms = []
        categories = set()
        
        for term in terms:
            entity = self.map_term(term)
            if entity:
                mapped_terms.append(entity)
                mapping = self.get_term_mapping(entity.entity_value)
                if mapping:
                    categories.add(mapping.category)
        
        # Check for incompatible combinations
        incompatible_combinations = [
            {"cash_flow_statement", "income_statement", "balance_sheet"}  # Mixed statement types
        ]
        
        is_valid = True
        warnings = []
        
        for incompatible_set in incompatible_combinations:
            if len(categories.intersection(incompatible_set)) > 1:
                is_valid = False
                warnings.append(f"Mixing terms from different financial statements: {categories}")
        
        return {
            "is_valid": is_valid,
            "warnings": warnings,
            "mapped_terms": mapped_terms,
            "categories": list(categories)
        }
    
    def get_related_terms(self, term: str) -> List[str]:
        """Get terms related to the given term (same category)"""
        entity = self.map_term(term)
        if not entity:
            return []
        
        mapping = self.get_term_mapping(entity.entity_value)
        if not mapping:
            return []
        
        # Get other terms in the same category
        related = self.get_terms_by_category(mapping.category)
        return [t for t in related if t != entity.entity_value]
    
    def set_similarity_threshold(self, threshold: float) -> None:
        """Set the similarity threshold for fuzzy matching"""
        if 0.0 <= threshold <= 1.0:
            self.similarity_threshold = threshold
        else:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
    
    def get_all_terms(self) -> List[str]:
        """Get all available canonical terms"""
        return list(self.term_mappings.keys())
    
    def get_term_statistics(self) -> Dict[str, Any]:
        """Get statistics about the term mappings"""
        categories = {}
        total_synonyms = 0
        
        for mapping in self.term_mappings.values():
            category = mapping.category
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
            total_synonyms += len(mapping.synonyms)
        
        return {
            "total_terms": len(self.term_mappings),
            "total_synonyms": total_synonyms,
            "categories": categories,
            "average_synonyms_per_term": total_synonyms / len(self.term_mappings) if self.term_mappings else 0
        }