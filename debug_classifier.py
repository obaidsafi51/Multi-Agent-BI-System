#!/usr/bin/env python3
"""
Debug the query classifier to see why 'what is the cashflow of 2024?' is still using fast_path
"""

import sys
sys.path.append('/home/obaidsafi31/Desktop/Agentic BI /agents/nlp-agent/src')

from query_classifier import QueryClassifier, ProcessingPath

def test_classifier():
    classifier = QueryClassifier()
    
    test_queries = [
        "what is the cashflow of 2024?",
        "what is revenue?",
        "show revenue of 2024",
        "total profit last year",
        "what is profit margin?"
    ]
    
    for query in test_queries:
        classification = classifier.classify_query(query)
        
        print(f"\nQuery: '{query}'")
        print(f"Complexity: {classification.complexity.value}")
        print(f"Processing Path: {classification.processing_path.value}") 
        print(f"Confidence: {classification.confidence_score}")
        print(f"Reasoning: {classification.reasoning}")
        print("-" * 60)

if __name__ == "__main__":
    test_classifier()
