"""
Similarity matching algorithm for unknown financial terms with configurable thresholds.
"""

import re
from typing import List, Tuple, Dict, Optional, Set, Any
from difflib import SequenceMatcher
import math


from .types import SimilarityMatch


class SimilarityMatcher:
    """Advanced similarity matching for financial terms"""
    
    def __init__(self, similarity_threshold: float = 0.7, include_saas_metrics: bool = False):
        """Initialize similarity matcher with configurable threshold.
        Args:
            similarity_threshold: threshold for fuzzy matching (0-1)
            include_saas_metrics: include customer/SaaS metrics (LTV, CAC, ARR, MRR) in abbreviation mapping
        """
        self.similarity_threshold = similarity_threshold
        self.include_saas_metrics = include_saas_metrics
        self.phonetic_threshold = 0.6
        self.semantic_threshold = 0.8
        
        # Common financial term abbreviations and variations
        # SaaS metrics can be included via include_saas_metrics flag
        base_abbreviations = {
            "rev": "revenue",
            "revs": "revenue", 
            "sales": "revenue",
            "income": "revenue",
            "turnover": "revenue",
            "p&l": "profit",
            "pnl": "profit",
            "profit": "net_profit",
            "earnings": "net_profit",
            "ebitda": "operating_profit",
            "cf": "cash_flow",
            "ocf": "operating_cash_flow",
            "fcf": "free_cash_flow",
            "capex": "capital_expenditure",
            "opex": "operating_expenses",
            "cogs": "cost_of_goods_sold",
            "sga": "selling_general_administrative",
            "r&d": "research_development",
            "rnd": "research_development",
            "roi": "return_on_investment",
            "roe": "return_on_equity",
            "roa": "return_on_assets",
            "d/e": "debt_to_equity",
            "de": "debt_to_equity",
            "cr": "current_ratio",
            "qr": "quick_ratio",
            "ar": "accounts_receivable",
            "ap": "accounts_payable",
            "wc": "working_capital",
            "nwc": "net_working_capital",
            "churn": "churn_rate",
            "nps": "net_promoter_score",
            "kpi": "key_performance_indicator",
            "ytd": "year_to_date",
            "qtd": "quarter_to_date",
            "mtd": "month_to_date",
            "yoy": "year_over_year",
            "qoq": "quarter_over_quarter",
            "mom": "month_over_month"
        }
        # Initialize abbreviation_map and optionally include SaaS metrics
        self.abbreviation_map = base_abbreviations.copy()
        if self.include_saas_metrics:
            self.abbreviation_map.update({
                "ltv": "lifetime_value",
                "cac": "customer_acquisition_cost",
                "arr": "annual_recurring_revenue",
                "mrr": "monthly_recurring_revenue",
            })
        
        # Common misspellings and typos
        self.common_misspellings = {
            "revenu": "revenue",
            "reveue": "revenue",
            "reveneu": "revenue",
            "proffit": "profit",
            "prfit": "profit",
            "cashflow": "cash_flow",
            "cash-flow": "cash_flow",
            "expences": "expenses",
            "expensis": "expenses",
            "margine": "margin",
            "margen": "margin",
            "assests": "assets",
            "liabilites": "liabilities",
            "liabilitys": "liabilities",
            "equaty": "equity",
            "equety": "equity"
        }
        
        # Semantic groups for context-aware matching
        self.semantic_groups = {
            "revenue_terms": ["revenue", "sales", "income", "turnover", "receipts", "earnings"],
            "profit_terms": ["profit", "earnings", "net_income", "bottom_line", "surplus"],
            "cash_terms": ["cash", "liquidity", "cash_flow", "cash_position"],
            "expense_terms": ["expenses", "costs", "expenditure", "spending", "outlay"],
            "ratio_terms": ["ratio", "percentage", "rate", "proportion", "multiple"],
            "time_terms": ["quarterly", "monthly", "yearly", "annual", "period"],
            "comparison_terms": ["versus", "compared", "against", "over", "growth"]
        }
    
    def find_best_matches(self, unknown_term: str, known_terms: List[str], 
                         limit: int = 5) -> List[SimilarityMatch]:
        """Find the best matching terms for an unknown term"""
        unknown_term = self._normalize_term(unknown_term)
        matches = []
        
        for known_term in known_terms:
            normalized_known = self._normalize_term(known_term)
            
            # Try different matching strategies
            similarity_results = [
                self._exact_match(unknown_term, normalized_known),
                self._abbreviation_match(unknown_term, normalized_known),
                self._fuzzy_match(unknown_term, normalized_known),
                self._phonetic_match(unknown_term, normalized_known),
                self._semantic_match(unknown_term, normalized_known),
                self._partial_match(unknown_term, normalized_known),
                self._edit_distance_match(unknown_term, normalized_known)
            ]
            # Remove None results to avoid issues with max()
            valid_results = [result for result in similarity_results if result]
            if not valid_results:
                continue
            
            # Get the best match from valid strategies
            best_match = max(valid_results, key=lambda x: x.similarity_score)
            
            if best_match and best_match.similarity_score >= self.similarity_threshold:
                matches.append(best_match)
        
        # Sort by similarity score and confidence
        matches.sort(key=lambda x: (x.similarity_score, x.confidence), reverse=True)
        return matches[:limit]
    
    def _normalize_term(self, term: str) -> str:
        """Normalize term for comparison"""
        # Convert to lowercase and remove special characters
        normalized = re.sub(r'[^\w\s]', '', term.lower().strip())
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def _exact_match(self, term1: str, term2: str) -> Optional[SimilarityMatch]:
        """Check for exact match"""
        if term1 == term2:
            return SimilarityMatch(
                term=term1,
                canonical_term=term2,
                similarity_score=1.0,
                match_type="exact",
                confidence=1.0
            )
        return None
    
    def _abbreviation_match(self, unknown_term: str, known_term: str) -> Optional[SimilarityMatch]:
        """Check for abbreviation matches"""
        # Check if unknown term is an abbreviation
        if unknown_term in self.abbreviation_map:
            expanded = self.abbreviation_map[unknown_term]
            if expanded == known_term or expanded in known_term:
                return SimilarityMatch(
                    term=unknown_term,
                    canonical_term=known_term,
                    similarity_score=0.95,
                    match_type="abbreviation",
                    confidence=0.9
                )
        
        # Check if known term has abbreviation that matches unknown
        for abbrev, full_term in self.abbreviation_map.items():
            if full_term == known_term and abbrev == unknown_term:
                return SimilarityMatch(
                    term=unknown_term,
                    canonical_term=known_term,
                    similarity_score=0.95,
                    match_type="abbreviation",
                    confidence=0.9
                )
        
        return None
    
    def _fuzzy_match(self, term1: str, term2: str) -> Optional[SimilarityMatch]:
        """Fuzzy string matching using sequence matcher"""
        similarity = SequenceMatcher(None, term1, term2).ratio()
        
        if similarity >= self.similarity_threshold:
            return SimilarityMatch(
                term=term1,
                canonical_term=term2,
                similarity_score=similarity,
                match_type="fuzzy",
                confidence=similarity * 0.8  # Lower confidence for fuzzy matches
            )
        
        return None
    
    def _phonetic_match(self, term1: str, term2: str) -> Optional[SimilarityMatch]:
        """Phonetic matching for similar sounding terms"""
        # Simple phonetic similarity based on consonant patterns
        consonants1 = self._extract_consonants(term1)
        consonants2 = self._extract_consonants(term2)
        
        if consonants1 and consonants2:
            similarity = SequenceMatcher(None, consonants1, consonants2).ratio()
            
            if similarity >= self.phonetic_threshold:
                return SimilarityMatch(
                    term=term1,
                    canonical_term=term2,
                    similarity_score=similarity,
                    match_type="phonetic",
                    confidence=similarity * 0.7  # Lower confidence for phonetic matches
                )
        
        return None
    
    def _extract_consonants(self, term: str) -> str:
        """Extract consonant pattern for phonetic matching"""
        vowels = set('aeiou')
        consonants = ''.join([c for c in term.lower() if c.isalpha() and c not in vowels])
        return consonants
    
    def _semantic_match(self, unknown_term: str, known_term: str) -> Optional[SimilarityMatch]:
        """Semantic matching based on term groups"""
        unknown_groups = self._get_semantic_groups(unknown_term)
        known_groups = self._get_semantic_groups(known_term)
        
        # Check for overlap in semantic groups
        common_groups = unknown_groups.intersection(known_groups)
        
        if common_groups:
            # Calculate semantic similarity based on group overlap
            total_groups = unknown_groups.union(known_groups)
            similarity = len(common_groups) / len(total_groups) if total_groups else 0
            
            if similarity >= self.semantic_threshold:
                return SimilarityMatch(
                    term=unknown_term,
                    canonical_term=known_term,
                    similarity_score=similarity,
                    match_type="semantic",
                    confidence=similarity * 0.85
                )
        
        return None
    
    def _get_semantic_groups(self, term: str) -> Set[str]:
        """Get semantic groups that contain the term"""
        groups = set()
        
        for group_name, terms in self.semantic_groups.items():
            if any(t in term or term in t for t in terms):
                groups.add(group_name)
        
        return groups
    
    def _partial_match(self, term1: str, term2: str) -> Optional[SimilarityMatch]:
        """Partial matching for compound terms"""
        words1 = term1.split()
        words2 = term2.split()
        
        if len(words1) > 1 or len(words2) > 1:
            # Check if any word from term1 matches any word from term2
            max_similarity = 0
            for word1 in words1:
                for word2 in words2:
                    similarity = SequenceMatcher(None, word1, word2).ratio()
                    max_similarity = max(max_similarity, similarity)
            
            # Also check if one term is contained in the other
            if term1 in term2 or term2 in term1:
                containment_similarity = min(len(term1), len(term2)) / max(len(term1), len(term2))
                max_similarity = max(max_similarity, containment_similarity)
            
            if max_similarity >= self.similarity_threshold:
                return SimilarityMatch(
                    term=term1,
                    canonical_term=term2,
                    similarity_score=max_similarity,
                    match_type="partial",
                    confidence=max_similarity * 0.75
                )
        
        return None
    
    def _edit_distance_match(self, term1: str, term2: str) -> Optional[SimilarityMatch]:
        """Edit distance based matching (Levenshtein distance)"""
        distance = self._levenshtein_distance(term1, term2)
        max_length = max(len(term1), len(term2))
        
        if max_length == 0:
            return None
        
        similarity = 1 - (distance / max_length)
        
        if similarity >= self.similarity_threshold:
            return SimilarityMatch(
                term=term1,
                canonical_term=term2,
                similarity_score=similarity,
                match_type="edit_distance",
                confidence=similarity * 0.8
            )
        
        return None
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def suggest_corrections(self, unknown_term: str) -> List[str]:
        """Suggest corrections for common misspellings"""
        normalized_term = self._normalize_term(unknown_term)
        
        # Check direct misspelling corrections
        if normalized_term in self.common_misspellings:
            return [self.common_misspellings[normalized_term]]
        
        # Check for partial misspelling matches
        suggestions = []
        for misspelling, correction in self.common_misspellings.items():
            if SequenceMatcher(None, normalized_term, misspelling).ratio() >= 0.8:
                suggestions.append(correction)
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def set_similarity_threshold(self, threshold: float) -> None:
        """Set the similarity threshold"""
        if 0.0 <= threshold <= 1.0:
            self.similarity_threshold = threshold
        else:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
    
    def set_phonetic_threshold(self, threshold: float) -> None:
        """Set the phonetic similarity threshold"""
        if 0.0 <= threshold <= 1.0:
            self.phonetic_threshold = threshold
        else:
            raise ValueError("Phonetic threshold must be between 0.0 and 1.0")
    
    def set_semantic_threshold(self, threshold: float) -> None:
        """Set the semantic similarity threshold"""
        if 0.0 <= threshold <= 1.0:
            self.semantic_threshold = threshold
        else:
            raise ValueError("Semantic threshold must be between 0.0 and 1.0")
    
    def add_abbreviation(self, abbreviation: str, full_term: str) -> None:
        """Add a new abbreviation mapping"""
        self.abbreviation_map[abbreviation.lower()] = full_term.lower()
    
    def add_misspelling(self, misspelling: str, correction: str) -> None:
        """Add a new misspelling correction"""
        self.common_misspellings[misspelling.lower()] = correction.lower()
    
    def add_semantic_group(self, group_name: str, terms: List[str]) -> None:
        """Add a new semantic group"""
        self.semantic_groups[group_name] = [term.lower() for term in terms]
    
    def get_match_statistics(self, matches: List[SimilarityMatch]) -> Dict[str, Any]:
        """Get statistics about match results"""
        if not matches:
            return {"total_matches": 0}
        
        match_types = {}
        total_similarity = 0
        total_confidence = 0
        
        for match in matches:
            match_types[match.match_type] = match_types.get(match.match_type, 0) + 1
            total_similarity += match.similarity_score
            total_confidence += match.confidence
        
        return {
            "total_matches": len(matches),
            "match_types": match_types,
            "average_similarity": total_similarity / len(matches),
            "average_confidence": total_confidence / len(matches),
            "best_match": matches[0] if matches else None
        }