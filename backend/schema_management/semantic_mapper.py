"""
Semantic Schema Mapper for NLP-based database schema analysis.

This module provides intelligent mapping between business terms and database schema elements
using semantic analysis, similarity matching, and machine learning techniques.
"""

import re
import asyncio
import logging
import json
import pickle
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import difflib

# Core dependencies
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
    NLTP_AVAILABLE = True
except ImportError:
    NLTP_AVAILABLE = False
    import warnings
    warnings.warn("Advanced NLP dependencies not available. Using fallback fuzzy matching.")

try:
    from .models import TableSchema, ColumnInfo, TableInfo
    from .config import MCPSchemaConfig
except ImportError:
    # Fallback for direct execution
    from models import TableSchema, ColumnInfo, TableInfo
    from config import MCPSchemaConfig

logger = logging.getLogger(__name__)


@dataclass
class SemanticMapping:
    """Represents a semantic mapping between a business term and schema element."""
    business_term: str
    schema_element_type: str  # 'table', 'column', 'index'
    schema_element_path: str  # e.g., 'database.table.column'
    confidence_score: float
    similarity_type: str  # 'semantic', 'fuzzy', 'exact', 'learned'
    context_match: bool
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class BusinessTerm:
    """Represents a business term with its variants and context."""
    primary_term: str
    synonyms: List[str]
    category: str  # e.g., 'financial', 'operational', 'customer'
    description: Optional[str]
    context_keywords: List[str]
    usage_frequency: int = 0


@dataclass
class SchemaElement:
    """Enhanced schema element with semantic metadata."""
    element_type: str  # 'table', 'column', 'index'
    full_path: str
    name: str
    description: Optional[str]
    semantic_tags: List[str]
    business_concepts: List[str]
    data_type: Optional[str]
    sample_values: Optional[List[str]]
    usage_patterns: Dict[str, Any]


@dataclass
class MappingCandidate:
    """Candidate mapping with detailed scoring information."""
    schema_element: SchemaElement
    similarity_scores: Dict[str, float]
    confidence_score: float
    match_reasons: List[str]
    context_relevance: float


class SemanticMappingConfig:
    """Configuration for semantic mapping operations."""
    
    def __init__(
        self,
        confidence_threshold: float = 0.7,
        max_suggestions: int = 5,
        enable_fuzzy_matching: bool = True,
        enable_semantic_similarity: bool = True,
        fuzzy_threshold: float = 0.6,
        semantic_threshold: float = 0.5,
        learning_enabled: bool = True,
        cache_embeddings: bool = True,
        vectorizer_max_features: int = 5000,
        min_term_frequency: int = 1
    ):
        self.confidence_threshold = confidence_threshold
        self.max_suggestions = max_suggestions
        self.enable_fuzzy_matching = enable_fuzzy_matching
        self.enable_semantic_similarity = enable_semantic_similarity
        self.fuzzy_threshold = fuzzy_threshold
        self.semantic_threshold = semantic_threshold
        self.learning_enabled = learning_enabled
        self.cache_embeddings = cache_embeddings
        self.vectorizer_max_features = vectorizer_max_features
        self.min_term_frequency = min_term_frequency

    @classmethod
    def from_env(cls) -> 'SemanticMappingConfig':
        """Create configuration from environment variables."""
        import os
        return cls(
            confidence_threshold=float(os.getenv('SEMANTIC_CONFIDENCE_THRESHOLD', '0.7')),
            max_suggestions=int(os.getenv('SEMANTIC_MAX_SUGGESTIONS', '5')),
            enable_fuzzy_matching=os.getenv('SEMANTIC_ENABLE_FUZZY', 'true').lower() == 'true',
            enable_semantic_similarity=os.getenv('SEMANTIC_ENABLE_SIMILARITY', 'true').lower() == 'true',
            fuzzy_threshold=float(os.getenv('SEMANTIC_FUZZY_THRESHOLD', '0.6')),
            semantic_threshold=float(os.getenv('SEMANTIC_SIMILARITY_THRESHOLD', '0.5')),
            learning_enabled=os.getenv('SEMANTIC_LEARNING_ENABLED', 'true').lower() == 'true',
            cache_embeddings=os.getenv('SEMANTIC_CACHE_EMBEDDINGS', 'true').lower() == 'true'
        )


class SemanticSchemaMapper:
    """
    Maps business terms to database schema elements using semantic analysis.
    
    Features:
    - Cosine similarity using TF-IDF vectors
    - Fuzzy string matching
    - Business term synonym recognition
    - Confidence scoring and ranking
    - Learning from successful mappings
    - Context-aware matching
    """
    
    def __init__(
        self,
        config: Optional[SemanticMappingConfig] = None,
        business_terms_path: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize semantic schema mapper.
        
        Args:
            config: Semantic mapping configuration
            business_terms_path: Path to business terms configuration file
            cache_dir: Directory for caching embeddings and models
        """
        self.config = config or SemanticMappingConfig.from_env()
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/semantic_mapping")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize NLP components
        self.lemmatizer = None
        self.stop_words = set()
        self.vectorizer = None
        
        if NLTP_AVAILABLE:
            self._initialize_nlp_components()
        
        # Schema and business term storage
        self.schema_elements: List[SchemaElement] = []
        self.business_terms: Dict[str, BusinessTerm] = {}
        self.learned_mappings: Dict[str, List[SemanticMapping]] = {}
        
        # Similarity models
        self.tfidf_matrix = None
        self.element_texts: List[str] = []
        
        # Load business terms if provided
        if business_terms_path:
            self.load_business_terms(business_terms_path)
        else:
            self._load_default_business_terms()
        
        logger.info(f"Initialized SemanticSchemaMapper with {len(self.business_terms)} business terms")
    
    def _initialize_nlp_components(self):
        """Initialize NLTK components for text processing."""
        try:
            # Download required NLTK data
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            
            self.lemmatizer = WordNetLemmatizer()
            self.stop_words = set(stopwords.words('english'))
            
            # Initialize TF-IDF vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=self.config.vectorizer_max_features,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=self.config.min_term_frequency,
                lowercase=True,
                token_pattern=r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'  # Match database identifiers
            )
            
            logger.info("NLP components initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize NLP components: {e}")
            self.lemmatizer = None
            self.stop_words = set()
    
    def _load_default_business_terms(self):
        """Load default business terms for common BI scenarios."""
        default_terms = {
            # Financial terms
            'revenue': BusinessTerm(
                primary_term='revenue',
                synonyms=['sales', 'income', 'earnings', 'turnover', 'receipts'],
                category='financial',
                description='Total income generated from business operations',
                context_keywords=['financial', 'money', 'sales', 'income']
            ),
            'profit': BusinessTerm(
                primary_term='profit',
                synonyms=['earnings', 'net_income', 'profit_margin', 'gain'],
                category='financial',
                description='Financial gain after expenses',
                context_keywords=['financial', 'earnings', 'margin', 'net']
            ),
            'cost': BusinessTerm(
                primary_term='cost',
                synonyms=['expense', 'expenditure', 'spending', 'outlay'],
                category='financial',
                description='Amount spent on business operations',
                context_keywords=['financial', 'expense', 'spending', 'budget']
            ),
            
            # Customer terms
            'customer': BusinessTerm(
                primary_term='customer',
                synonyms=['client', 'buyer', 'consumer', 'user', 'account'],
                category='customer',
                description='Person or entity that purchases goods or services',
                context_keywords=['customer', 'client', 'user', 'buyer']
            ),
            'order': BusinessTerm(
                primary_term='order',
                synonyms=['purchase', 'transaction', 'sale', 'booking'],
                category='operational',
                description='Customer request for goods or services',
                context_keywords=['order', 'purchase', 'transaction', 'sale']
            ),
            
            # Time-based terms
            'date': BusinessTerm(
                primary_term='date',
                synonyms=['time', 'timestamp', 'datetime', 'created_at', 'updated_at'],
                category='temporal',
                description='Point in time when something occurred',
                context_keywords=['date', 'time', 'when', 'created', 'updated']
            ),
            'quarter': BusinessTerm(
                primary_term='quarter',
                synonyms=['q1', 'q2', 'q3', 'q4', 'quarterly', 'fiscal_quarter'],
                category='temporal',
                description='Three-month period in business reporting',
                context_keywords=['quarter', 'quarterly', 'fiscal', 'period']
            ),
            
            # Product terms
            'product': BusinessTerm(
                primary_term='product',
                synonyms=['item', 'sku', 'merchandise', 'goods', 'service'],
                category='product',
                description='Goods or services offered by the business',
                context_keywords=['product', 'item', 'sku', 'goods', 'service']
            ),
            
            # Geographic terms
            'region': BusinessTerm(
                primary_term='region',
                synonyms=['area', 'territory', 'zone', 'location', 'geography'],
                category='geographic',
                description='Geographic area for business operations',
                context_keywords=['region', 'area', 'location', 'geography', 'territory']
            ),
            'country': BusinessTerm(
                primary_term='country',
                synonyms=['nation', 'state', 'territory'],
                category='geographic',
                description='National territory for business operations',
                context_keywords=['country', 'nation', 'territory', 'state']
            )
        }
        
        self.business_terms = default_terms
        logger.info(f"Loaded {len(default_terms)} default business terms")
    
    def load_business_terms(self, file_path: str):
        """
        Load business terms from a configuration file.
        
        Args:
            file_path: Path to business terms JSON file
        """
        try:
            with open(file_path, 'r') as f:
                terms_data = json.load(f)
            
            loaded_terms = {}
            for term_id, term_data in terms_data.items():
                loaded_terms[term_id] = BusinessTerm(
                    primary_term=term_data['primary_term'],
                    synonyms=term_data.get('synonyms', []),
                    category=term_data.get('category', 'general'),
                    description=term_data.get('description'),
                    context_keywords=term_data.get('context_keywords', []),
                    usage_frequency=term_data.get('usage_frequency', 0)
                )
            
            self.business_terms.update(loaded_terms)
            logger.info(f"Loaded {len(loaded_terms)} business terms from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load business terms from {file_path}: {e}")
    
    def save_business_terms(self, file_path: str):
        """
        Save current business terms to a configuration file.
        
        Args:
            file_path: Path to save business terms JSON file
        """
        try:
            terms_data = {}
            for term_id, term in self.business_terms.items():
                terms_data[term_id] = asdict(term)
            
            with open(file_path, 'w') as f:
                json.dump(terms_data, f, indent=2, default=str)
            
            logger.info(f"Saved {len(terms_data)} business terms to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save business terms to {file_path}: {e}")
    
    def add_business_term(self, term: BusinessTerm):
        """
        Add a new business term to the mapper.
        
        Args:
            term: Business term to add
        """
        term_id = term.primary_term.lower().replace(' ', '_')
        self.business_terms[term_id] = term
        logger.debug(f"Added business term: {term.primary_term}")
    
    async def analyze_table_schema(self, table_schema: TableSchema) -> SchemaElement:
        """
        Analyze a table schema to extract semantic information.
        
        Args:
            table_schema: Table schema to analyze
            
        Returns:
            Enhanced schema element with semantic metadata
        """
        # Extract semantic information from table name and comment
        table_name = table_schema.table
        table_comment = table_schema.table_info.comment if table_schema.table_info else None
        
        # Analyze table name for business concepts
        business_concepts = self._extract_business_concepts(table_name, table_comment)
        semantic_tags = self._generate_semantic_tags(table_name, table_comment)
        
        # Create table schema element
        table_element = SchemaElement(
            element_type='table',
            full_path=f"{table_schema.database}.{table_schema.table}",
            name=table_name,
            description=table_comment,
            semantic_tags=semantic_tags,
            business_concepts=business_concepts,
            data_type=None,
            sample_values=None,
            usage_patterns={}
        )
        
        # Analyze columns
        column_elements = []
        for column in table_schema.columns:
            column_concepts = self._extract_business_concepts(column.name, column.comment)
            column_tags = self._generate_semantic_tags(column.name, column.comment)
            
            column_element = SchemaElement(
                element_type='column',
                full_path=f"{table_schema.database}.{table_schema.table}.{column.name}",
                name=column.name,
                description=column.comment,
                semantic_tags=column_tags,
                business_concepts=column_concepts,
                data_type=column.data_type,
                sample_values=None,  # Could be populated from sample queries
                usage_patterns={}
            )
            column_elements.append(column_element)
        
        # Store schema elements for similarity matching
        self.schema_elements.append(table_element)
        self.schema_elements.extend(column_elements)
        
        # Update TF-IDF matrix with new elements
        await self._update_similarity_models()
        
        return table_element
    
    def _extract_business_concepts(self, name: str, comment: Optional[str]) -> List[str]:
        """
        Extract business concepts from schema element name and comment.
        
        Args:
            name: Schema element name
            comment: Optional comment/description
            
        Returns:
            List of identified business concepts
        """
        concepts = []
        text_to_analyze = [name]
        
        if comment:
            text_to_analyze.append(comment)
        
        # Combine all text for analysis
        combined_text = ' '.join(text_to_analyze).lower()
        
        # Check for business term matches
        for term_id, business_term in self.business_terms.items():
            # Check primary term
            if business_term.primary_term.lower() in combined_text:
                concepts.append(business_term.primary_term)
                continue
            
            # Check synonyms
            for synonym in business_term.synonyms:
                if synonym.lower() in combined_text:
                    concepts.append(business_term.primary_term)
                    break
            
            # Check context keywords
            context_matches = sum(1 for keyword in business_term.context_keywords 
                                if keyword.lower() in combined_text)
            if context_matches >= 2:  # Require multiple context matches
                concepts.append(business_term.primary_term)
        
        return list(set(concepts))  # Remove duplicates
    
    def _generate_semantic_tags(self, name: str, comment: Optional[str]) -> List[str]:
        """
        Generate semantic tags for schema elements.
        
        Args:
            name: Schema element name
            comment: Optional comment/description
            
        Returns:
            List of semantic tags
        """
        tags = []
        
        # Common patterns in database naming
        name_lower = name.lower()
        
        # Data type indicators
        if any(suffix in name_lower for suffix in ['_id', '_key', 'id']):
            tags.append('identifier')
        
        if any(suffix in name_lower for suffix in ['_date', '_time', '_at', 'created', 'updated']):
            tags.append('temporal')
        
        if any(prefix in name_lower for prefix in ['is_', 'has_', 'can_']):
            tags.append('boolean')
        
        if any(word in name_lower for word in ['amount', 'price', 'cost', 'value', 'total']):
            tags.append('monetary')
        
        if any(word in name_lower for word in ['count', 'number', 'qty', 'quantity']):
            tags.append('numeric')
        
        if any(word in name_lower for word in ['name', 'title', 'description', 'text']):
            tags.append('textual')
        
        # Business domain tags
        if any(word in name_lower for word in ['customer', 'client', 'user']):
            tags.append('customer_related')
        
        if any(word in name_lower for word in ['order', 'transaction', 'purchase', 'sale']):
            tags.append('transaction_related')
        
        if any(word in name_lower for word in ['product', 'item', 'sku']):
            tags.append('product_related')
        
        # Analyze comment if available
        if comment:
            comment_lower = comment.lower()
            if any(word in comment_lower for word in ['foreign key', 'references']):
                tags.append('foreign_key')
            
            if any(word in comment_lower for word in ['primary key', 'unique']):
                tags.append('primary_key')
        
        return tags
    
    async def _update_similarity_models(self):
        """Update TF-IDF models with current schema elements."""
        if not self.config.enable_semantic_similarity or not NLTP_AVAILABLE:
            return
        
        try:
            # Prepare texts for vectorization
            self.element_texts = []
            for element in self.schema_elements:
                # Combine name, description, and semantic information
                text_parts = [element.name]
                
                if element.description:
                    text_parts.append(element.description)
                
                # Add business concepts and semantic tags
                text_parts.extend(element.business_concepts)
                text_parts.extend(element.semantic_tags)
                
                # Preprocess text
                combined_text = ' '.join(text_parts)
                processed_text = self._preprocess_text(combined_text)
                self.element_texts.append(processed_text)
            
            if self.element_texts:
                # Fit TF-IDF vectorizer
                self.tfidf_matrix = self.vectorizer.fit_transform(self.element_texts)
                logger.debug(f"Updated TF-IDF matrix with {len(self.element_texts)} schema elements")
            
        except Exception as e:
            logger.error(f"Failed to update similarity models: {e}")
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for similarity analysis.
        
        Args:
            text: Raw text to preprocess
            
        Returns:
            Preprocessed text
        """
        if not NLTP_AVAILABLE or not self.lemmatizer:
            # Fallback preprocessing
            return re.sub(r'[^a-zA-Z0-9\s_]', ' ', text.lower())
        
        try:
            # Tokenize and clean
            tokens = word_tokenize(text.lower())
            
            # Remove non-alphabetic tokens and stopwords
            tokens = [token for token in tokens 
                     if token.isalpha() and token not in self.stop_words]
            
            # Lemmatize
            tokens = [self.lemmatizer.lemmatize(token) for token in tokens]
            
            return ' '.join(tokens)
            
        except Exception as e:
            logger.warning(f"Text preprocessing failed: {e}")
            # Fallback to simple cleaning
            return re.sub(r'[^a-zA-Z0-9\s_]', ' ', text.lower())
    
    async def map_business_term(
        self,
        term: str,
        context: Optional[str] = None,
        schema_filter: Optional[Dict[str, Any]] = None
    ) -> List[SemanticMapping]:
        """
        Map a business term to database schema elements.
        
        Args:
            term: Business term to map
            context: Optional context to improve matching
            schema_filter: Optional filter to limit search scope
            
        Returns:
            List of semantic mappings ranked by confidence
        """
        # Check learned mappings first
        if self.config.learning_enabled:
            learned = self._get_learned_mappings(term)
            if learned:
                logger.debug(f"Found {len(learned)} learned mappings for '{term}'")
                return learned[:self.config.max_suggestions]
        
        # Find candidate mappings
        candidates = await self._find_mapping_candidates(term, context, schema_filter)
        
        # Rank candidates by confidence
        ranked_mappings = self._rank_mapping_candidates(term, candidates, context)
        
        # Filter by confidence threshold
        valid_mappings = [
            mapping for mapping in ranked_mappings
            if mapping.confidence_score >= self.config.confidence_threshold
        ]
        
        # Limit to maximum suggestions
        result_mappings = valid_mappings[:self.config.max_suggestions]
        
        logger.info(f"Mapped '{term}' to {len(result_mappings)} schema elements")
        return result_mappings
    
    async def _find_mapping_candidates(
        self,
        term: str,
        context: Optional[str],
        schema_filter: Optional[Dict[str, Any]]
    ) -> List[MappingCandidate]:
        """
        Find candidate schema elements for mapping.
        
        Args:
            term: Business term to map
            context: Optional context
            schema_filter: Optional filter criteria
            
        Returns:
            List of mapping candidates
        """
        candidates = []
        
        # Filter schema elements if requested
        elements_to_search = self.schema_elements
        if schema_filter:
            elements_to_search = self._filter_schema_elements(elements_to_search, schema_filter)
        
        for element in elements_to_search:
            candidate = await self._evaluate_element_as_candidate(term, element, context)
            if candidate and candidate.confidence_score > 0:
                candidates.append(candidate)
        
        return candidates
    
    def _filter_schema_elements(
        self,
        elements: List[SchemaElement],
        filter_criteria: Dict[str, Any]
    ) -> List[SchemaElement]:
        """
        Filter schema elements based on criteria.
        
        Args:
            elements: Schema elements to filter
            filter_criteria: Filter criteria
            
        Returns:
            Filtered schema elements
        """
        filtered = elements
        
        if 'element_type' in filter_criteria:
            element_type = filter_criteria['element_type']
            filtered = [e for e in filtered if e.element_type == element_type]
        
        if 'database' in filter_criteria:
            database = filter_criteria['database']
            filtered = [e for e in filtered if e.full_path.startswith(f"{database}.")]
        
        if 'table' in filter_criteria:
            table = filter_criteria['table']
            filtered = [e for e in filtered 
                       if len(e.full_path.split('.')) >= 2 and e.full_path.split('.')[1] == table]
        
        if 'semantic_tags' in filter_criteria:
            required_tags = filter_criteria['semantic_tags']
            if isinstance(required_tags, str):
                required_tags = [required_tags]
            filtered = [e for e in filtered 
                       if any(tag in e.semantic_tags for tag in required_tags)]
        
        return filtered
    
    async def _evaluate_element_as_candidate(
        self,
        term: str,
        element: SchemaElement,
        context: Optional[str]
    ) -> Optional[MappingCandidate]:
        """
        Evaluate a schema element as a mapping candidate.
        
        Args:
            term: Business term
            element: Schema element to evaluate
            context: Optional context
            
        Returns:
            Mapping candidate or None if not suitable
        """
        similarity_scores = {}
        match_reasons = []
        context_relevance = 0.0
        
        # Exact match check
        if term.lower() == element.name.lower():
            similarity_scores['exact'] = 1.0
            match_reasons.append('exact_name_match')
        
        # Fuzzy matching
        if self.config.enable_fuzzy_matching:
            fuzzy_score = self._calculate_fuzzy_similarity(term, element)
            similarity_scores['fuzzy'] = fuzzy_score
            if fuzzy_score >= self.config.fuzzy_threshold:
                match_reasons.append(f'fuzzy_match_{fuzzy_score:.2f}')
        
        # Semantic similarity
        if self.config.enable_semantic_similarity and self.tfidf_matrix is not None:
            semantic_score = await self._calculate_semantic_similarity(term, element)
            similarity_scores['semantic'] = semantic_score
            if semantic_score >= self.config.semantic_threshold:
                match_reasons.append(f'semantic_match_{semantic_score:.2f}')
        
        # Business concept matching
        concept_score = self._calculate_concept_similarity(term, element)
        similarity_scores['concept'] = concept_score
        if concept_score > 0:
            match_reasons.append(f'concept_match_{concept_score:.2f}')
        
        # Context relevance
        if context:
            context_relevance = self._calculate_context_relevance(context, element)
            if context_relevance > 0.5:
                match_reasons.append(f'context_relevant_{context_relevance:.2f}')
        
        # Calculate overall confidence score
        confidence_score = self._calculate_confidence_score(similarity_scores, context_relevance)
        
        if confidence_score > 0:
            return MappingCandidate(
                schema_element=element,
                similarity_scores=similarity_scores,
                confidence_score=confidence_score,
                match_reasons=match_reasons,
                context_relevance=context_relevance
            )
        
        return None
    
    def _calculate_fuzzy_similarity(self, term: str, element: SchemaElement) -> float:
        """
        Calculate fuzzy string similarity between term and element.
        
        Args:
            term: Business term
            element: Schema element
            
        Returns:
            Fuzzy similarity score (0.0 to 1.0)
        """
        # Compare with element name
        name_similarity = difflib.SequenceMatcher(None, term.lower(), element.name.lower()).ratio()
        
        # Compare with description if available
        desc_similarity = 0.0
        if element.description:
            desc_similarity = difflib.SequenceMatcher(
                None, term.lower(), element.description.lower()
            ).ratio()
        
        # Compare with business concepts
        concept_similarity = 0.0
        if element.business_concepts:
            concept_similarities = [
                difflib.SequenceMatcher(None, term.lower(), concept.lower()).ratio()
                for concept in element.business_concepts
            ]
            concept_similarity = max(concept_similarities) if concept_similarities else 0.0
        
        # Return the highest similarity
        return max(name_similarity, desc_similarity, concept_similarity)
    
    async def _calculate_semantic_similarity(self, term: str, element: SchemaElement) -> float:
        """
        Calculate semantic similarity using TF-IDF vectors.
        
        Args:
            term: Business term
            element: Schema element
            
        Returns:
            Semantic similarity score (0.0 to 1.0)
        """
        if not NLTP_AVAILABLE or self.tfidf_matrix is None:
            return 0.0
        
        try:
            # Find element index
            element_index = None
            for i, elem in enumerate(self.schema_elements):
                if elem.full_path == element.full_path:
                    element_index = i
                    break
            
            if element_index is None:
                return 0.0
            
            # Preprocess term and vectorize
            processed_term = self._preprocess_text(term)
            term_vector = self.vectorizer.transform([processed_term])
            
            # Calculate cosine similarity
            element_vector = self.tfidf_matrix[element_index:element_index+1]
            similarity = cosine_similarity(term_vector, element_vector)[0][0]
            
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return 0.0
    
    def _calculate_concept_similarity(self, term: str, element: SchemaElement) -> float:
        """
        Calculate similarity based on business concepts.
        
        Args:
            term: Business term
            element: Schema element
            
        Returns:
            Concept similarity score (0.0 to 1.0)
        """
        if not element.business_concepts:
            return 0.0
        
        # Check if term matches any business concept directly
        term_lower = term.lower()
        
        # Direct match
        if term_lower in [concept.lower() for concept in element.business_concepts]:
            return 1.0
        
        # Check business term synonyms
        for business_term in self.business_terms.values():
            if business_term.primary_term.lower() == term_lower:
                # Check if any synonyms match element concepts
                for synonym in business_term.synonyms:
                    if synonym.lower() in [concept.lower() for concept in element.business_concepts]:
                        return 0.8
                break
        
        # Fuzzy concept matching
        max_fuzzy = 0.0
        for concept in element.business_concepts:
            fuzzy_score = difflib.SequenceMatcher(None, term_lower, concept.lower()).ratio()
            max_fuzzy = max(max_fuzzy, fuzzy_score)
        
        return max_fuzzy * 0.6  # Reduce weight for fuzzy concept matches
    
    def _calculate_context_relevance(self, context: str, element: SchemaElement) -> float:
        """
        Calculate relevance of schema element to provided context.
        
        Args:
            context: Context string
            element: Schema element
            
        Returns:
            Context relevance score (0.0 to 1.0)
        """
        if not context:
            return 0.0
        
        context_lower = context.lower()
        relevance_factors = []
        
        # Check if element path components appear in context
        path_parts = element.full_path.split('.')
        for part in path_parts:
            if part.lower() in context_lower:
                relevance_factors.append(0.3)
        
        # Check if element description mentions context terms
        if element.description:
            desc_lower = element.description.lower()
            context_words = context_lower.split()
            matches = sum(1 for word in context_words if word in desc_lower)
            if matches > 0:
                relevance_factors.append(matches / len(context_words) * 0.4)
        
        # Check semantic tags against context
        for tag in element.semantic_tags:
            if tag.lower() in context_lower:
                relevance_factors.append(0.2)
        
        # Check business concepts against context
        for concept in element.business_concepts:
            if concept.lower() in context_lower:
                relevance_factors.append(0.3)
        
        return min(1.0, sum(relevance_factors))
    
    def _calculate_confidence_score(
        self,
        similarity_scores: Dict[str, float],
        context_relevance: float
    ) -> float:
        """
        Calculate overall confidence score for a mapping.
        
        Args:
            similarity_scores: Dictionary of similarity scores
            context_relevance: Context relevance score
            
        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        # Weight different similarity types
        weights = {
            'exact': 0.4,
            'fuzzy': 0.25,
            'semantic': 0.25,
            'concept': 0.3
        }
        
        # Calculate weighted similarity score
        weighted_score = 0.0
        total_weight = 0.0
        
        for score_type, score in similarity_scores.items():
            if score_type in weights:
                weighted_score += score * weights[score_type]
                total_weight += weights[score_type]
        
        if total_weight > 0:
            base_score = weighted_score / total_weight
        else:
            base_score = 0.0
        
        # Apply context boost
        context_boost = context_relevance * 0.15
        final_score = min(1.0, base_score + context_boost)
        
        return final_score
    
    def _rank_mapping_candidates(
        self,
        term: str,
        candidates: List[MappingCandidate],
        context: Optional[str]
    ) -> List[SemanticMapping]:
        """
        Rank mapping candidates and convert to semantic mappings.
        
        Args:
            term: Business term
            candidates: Mapping candidates
            context: Optional context
            
        Returns:
            Ranked list of semantic mappings
        """
        # Sort candidates by confidence score
        sorted_candidates = sorted(candidates, key=lambda c: c.confidence_score, reverse=True)
        
        mappings = []
        for candidate in sorted_candidates:
            # Determine primary similarity type
            similarity_type = 'fuzzy'  # default
            max_score = 0.0
            for score_type, score in candidate.similarity_scores.items():
                if score > max_score:
                    max_score = score
                    similarity_type = score_type
            
            mapping = SemanticMapping(
                business_term=term,
                schema_element_type=candidate.schema_element.element_type,
                schema_element_path=candidate.schema_element.full_path,
                confidence_score=candidate.confidence_score,
                similarity_type=similarity_type,
                context_match=candidate.context_relevance > 0.5,
                metadata={
                    'similarity_scores': candidate.similarity_scores,
                    'match_reasons': candidate.match_reasons,
                    'context_relevance': candidate.context_relevance,
                    'element_name': candidate.schema_element.name,
                    'element_description': candidate.schema_element.description,
                    'semantic_tags': candidate.schema_element.semantic_tags,
                    'business_concepts': candidate.schema_element.business_concepts
                },
                created_at=datetime.now()
            )
            mappings.append(mapping)
        
        return mappings
    
    def _get_learned_mappings(self, term: str) -> List[SemanticMapping]:
        """
        Get previously learned mappings for a term.
        
        Args:
            term: Business term
            
        Returns:
            List of learned mappings
        """
        term_key = term.lower()
        return self.learned_mappings.get(term_key, [])
    
    def learn_successful_mapping(self, mapping: SemanticMapping, success_score: float = 1.0):
        """
        Learn from a successful mapping to improve future results.
        
        Args:
            mapping: Successful semantic mapping
            success_score: Score indicating mapping success (0.0 to 1.0)
        """
        if not self.config.learning_enabled:
            return
        
        term_key = mapping.business_term.lower()
        
        if term_key not in self.learned_mappings:
            self.learned_mappings[term_key] = []
        
        # Check if mapping already exists
        existing_mapping = None
        for learned in self.learned_mappings[term_key]:
            if learned.schema_element_path == mapping.schema_element_path:
                existing_mapping = learned
                break
        
        if existing_mapping:
            # Update confidence score based on success
            new_confidence = min(1.0, existing_mapping.confidence_score + success_score * 0.1)
            existing_mapping.confidence_score = new_confidence
            existing_mapping.similarity_type = 'learned'
        else:
            # Add new learned mapping
            learned_mapping = SemanticMapping(
                business_term=mapping.business_term,
                schema_element_type=mapping.schema_element_type,
                schema_element_path=mapping.schema_element_path,
                confidence_score=min(1.0, mapping.confidence_score + success_score * 0.2),
                similarity_type='learned',
                context_match=mapping.context_match,
                metadata=mapping.metadata.copy(),
                created_at=datetime.now()
            )
            self.learned_mappings[term_key].append(learned_mapping)
        
        # Sort by confidence score
        self.learned_mappings[term_key].sort(key=lambda m: m.confidence_score, reverse=True)
        
        # Keep only top mappings to avoid memory bloat
        max_learned_per_term = 10
        self.learned_mappings[term_key] = self.learned_mappings[term_key][:max_learned_per_term]
        
        logger.debug(f"Learned successful mapping for '{mapping.business_term}' -> '{mapping.schema_element_path}'")
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about semantic mappings.
        
        Returns:
            Dictionary with mapping statistics
        """
        stats = {
            'total_schema_elements': len(self.schema_elements),
            'total_business_terms': len(self.business_terms),
            'learned_mappings_count': sum(len(mappings) for mappings in self.learned_mappings.values()),
            'schema_element_types': {},
            'business_term_categories': {},
            'semantic_tags_distribution': {},
            'configuration': {
                'confidence_threshold': self.config.confidence_threshold,
                'max_suggestions': self.config.max_suggestions,
                'fuzzy_matching_enabled': self.config.enable_fuzzy_matching,
                'semantic_similarity_enabled': self.config.enable_semantic_similarity,
                'learning_enabled': self.config.learning_enabled
            }
        }
        
        # Count schema element types
        for element in self.schema_elements:
            element_type = element.element_type
            stats['schema_element_types'][element_type] = stats['schema_element_types'].get(element_type, 0) + 1
        
        # Count business term categories
        for term in self.business_terms.values():
            category = term.category
            stats['business_term_categories'][category] = stats['business_term_categories'].get(category, 0) + 1
        
        # Count semantic tags
        for element in self.schema_elements:
            for tag in element.semantic_tags:
                stats['semantic_tags_distribution'][tag] = stats['semantic_tags_distribution'].get(tag, 0) + 1
        
        return stats
    
    async def suggest_alternative_terms(self, failed_term: str, max_suggestions: int = 3) -> List[str]:
        """
        Suggest alternative business terms when mapping fails.
        
        Args:
            failed_term: Term that failed to map
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested alternative terms
        """
        suggestions = []
        
        # Find similar business terms using fuzzy matching
        for term_id, business_term in self.business_terms.items():
            # Check primary term
            similarity = difflib.SequenceMatcher(
                None, failed_term.lower(), business_term.primary_term.lower()
            ).ratio()
            
            if similarity >= 0.6:
                suggestions.append((business_term.primary_term, similarity))
            
            # Check synonyms
            for synonym in business_term.synonyms:
                synonym_similarity = difflib.SequenceMatcher(
                    None, failed_term.lower(), synonym.lower()
                ).ratio()
                
                if synonym_similarity >= 0.6:
                    suggestions.append((synonym, synonym_similarity))
        
        # Sort by similarity and remove duplicates
        unique_suggestions = {}
        for term, similarity in suggestions:
            if term not in unique_suggestions or unique_suggestions[term] < similarity:
                unique_suggestions[term] = similarity
        
        sorted_suggestions = sorted(
            unique_suggestions.keys(),
            key=lambda t: unique_suggestions[t],
            reverse=True
        )
        
        return sorted_suggestions[:max_suggestions]
    
    def save_learned_mappings(self, file_path: str):
        """
        Save learned mappings to a file.
        
        Args:
            file_path: Path to save learned mappings
        """
        try:
            # Convert mappings to serializable format
            serializable_mappings = {}
            for term, mappings in self.learned_mappings.items():
                serializable_mappings[term] = [asdict(mapping) for mapping in mappings]
            
            with open(file_path, 'w') as f:
                json.dump(serializable_mappings, f, indent=2, default=str)
            
            logger.info(f"Saved learned mappings to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save learned mappings: {e}")
    
    def load_learned_mappings(self, file_path: str):
        """
        Load learned mappings from a file.
        
        Args:
            file_path: Path to load learned mappings from
        """
        try:
            with open(file_path, 'r') as f:
                serializable_mappings = json.load(f)
            
            loaded_mappings = {}
            for term, mappings_data in serializable_mappings.items():
                mappings = []
                for mapping_data in mappings_data:
                    # Convert datetime string back to datetime object
                    if isinstance(mapping_data['created_at'], str):
                        mapping_data['created_at'] = datetime.fromisoformat(mapping_data['created_at'])
                    
                    mapping = SemanticMapping(**mapping_data)
                    mappings.append(mapping)
                
                loaded_mappings[term] = mappings
            
            self.learned_mappings.update(loaded_mappings)
            
            total_loaded = sum(len(mappings) for mappings in loaded_mappings.values())
            logger.info(f"Loaded {total_loaded} learned mappings from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load learned mappings: {e}")
