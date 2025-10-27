"""
Advanced Feature Engineering for Text Data.

This module provides a comprehensive suite of functions to extract a rich set
of features from raw text, designed to enhance the performance of machine
learning models for sentiment analysis and other NLP tasks.
"""

import re
import string
from collections import Counter
from typing import Any, Dict, List, Optional

import nltk
import textstat
from nltk.corpus import stopwords
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.tokenize import sent_tokenize, word_tokenize

from app.core.logging import get_logger

logger = get_logger(__name__)


class FeatureEngineer:
    """A comprehensive text feature engineering toolkit.

    This class encapsulates a wide range of feature extraction methods,
    transforming raw text into a rich, structured dictionary of numerical
    and categorical features suitable for machine learning models. It handles
    the download and setup of necessary NLTK resources in a controlled manner.
    """

    def __init__(self, download_nltk_data: bool = True):
        """Initializes the FeatureEngineer and downloads NLTK data if needed.

        Args:
            download_nltk_data: If True, downloads required NLTK data on
                initialization. Set to False in environments where data is
                pre-packaged.
        """
        if download_nltk_data:
            self._download_nltk_resources()

        self.lemmatizer = WordNetLemmatizer()
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words("english"))
        self.vader_analyzer = SentimentIntensityAnalyzer()

    def _download_nltk_resources(self) -> None:
        """Downloads all necessary NLTK resources for feature engineering.

        This method centralizes the downloading of NLTK data to avoid
        errors and ensure all components are available. It is designed to
        be fault-tolerant.
        """
        resources = [
            "punkt",
            "stopwords",
            "averaged_perceptron_tagger",
            "wordnet",
            "vader_lexicon",
        ]
        for resource in resources:
            try:
                nltk.data.find(f"tokenizers/{resource}")
            except LookupError:
                logger.info(f"Downloading NLTK resource: {resource}")
                try:
                    nltk.download(resource, quiet=True)
                except Exception as e:
                    logger.error(
                        f"Failed to download NLTK resource '{resource}': {e}",
                        exc_info=True,
                    )
                    # Decide if this should be a critical failure
                    # For now, we log and continue
                    pass

    def extract_features(self, text: str) -> Dict[str, Any]:
        """Orchestrates the extraction of all features from a given text.

        Args:
            text: The input text to be processed.

        Returns:
            A dictionary containing a comprehensive set of extracted features.
        """
        if not isinstance(text, str) or not text.strip():
            return {}

        words = word_tokenize(text.lower())
        sentences = sent_tokenize(text)

        features = {}
        features.update(self._text_statistics(text, words, sentences))
        features.update(self._lexical_diversity(words))
        features.update(self._sentiment_scores(text))
        features.update(self._readability_scores(text))
        features.update(self._pos_tagging_features(words))
        features.update(self._structural_and_stylistic_features(text, words))
        features.update(self._word_shape_and_type_features(words))

        return features

    def _text_statistics(
        self, text: str, words: List[str], sentences: List[str]
    ) -> Dict[str, Any]:
        """Calculates basic statistical features of the text."""
        char_count = len(text)
        word_count = len(words)
        sentence_count = len(sentences)

        return {
            "char_count": char_count,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_word_length": (char_count / word_count) if word_count > 0 else 0,
            "avg_sentence_length": (word_count / sentence_count)
            if sentence_count > 0
            else 0,
        }

    def _lexical_diversity(self, words: List[str]) -> Dict[str, Any]:
        """Calculates features related to lexical richness."""
        word_count = len(words)
        unique_words = set(words)
        unique_word_count = len(unique_words)
        stopwords_count = sum(1 for word in words if word in self.stop_words)

        return {
            "unique_word_count": unique_word_count,
            "lexical_richness": (unique_word_count / word_count) if word_count > 0 else 0,
            "stopwords_count": stopwords_count,
            "stopwords_ratio": (stopwords_count / word_count) if word_count > 0 else 0,
        }

    def _sentiment_scores(self, text: str) -> Dict[str, Any]:
        """Calculates VADER sentiment scores."""
        sentiment = self.vader_analyzer.polarity_scores(text)
        return {
            "vader_sentiment_compound": sentiment["compound"],
            "vader_sentiment_pos": sentiment["pos"],
            "vader_sentiment_neg": sentiment["neg"],
            "vader_sentiment_neu": sentiment["neu"],
        }

    def _readability_scores(self, text: str) -> Dict[str, Any]:
        """Calculates various readability metrics."""
        return {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
            "smog_index": textstat.smog_index(text),
            "coleman_liau_index": textstat.coleman_liau_index(text),
            "automated_readability_index": textstat.automated_readability_index(text),
            "dale_chall_readability_score": textstat.dale_chall_readability_score(text),
            "gunning_fog": textstat.gunning_fog(text),
        }

    def _pos_tagging_features(self, words: List[str]) -> Dict[str, Any]:
        """Calculates features based on Part-of-Speech (POS) tagging."""
        pos_tags = [tag for word, tag in nltk.pos_tag(words)]
        pos_counts = Counter(pos_tags)
        word_count = len(words)

        return {
            "noun_count": pos_counts.get("NN", 0) + pos_counts.get("NNS", 0),
            "verb_count": pos_counts.get("VB", 0) + pos_counts.get("VBP", 0),
            "adjective_count": pos_counts.get("JJ", 0),
            "adverb_count": pos_counts.get("RB", 0),
            "pronoun_count": pos_counts.get("PRP", 0),
            "noun_ratio": (pos_counts.get("NN", 0) / word_count) if word_count > 0 else 0,
            "verb_ratio": (pos_counts.get("VB", 0) / word_count) if word_count > 0 else 0,
            "adjective_ratio": (pos_counts.get("JJ", 0) / word_count) if word_count > 0 else 0,
        }

    def _structural_and_stylistic_features(
        self, text: str, words: List[str]
    ) -> Dict[str, Any]:
        """Extracts features related to text structure and style."""
        punctuation_count = sum(1 for char in text if char in string.punctuation)
        uppercase_word_count = sum(1 for word in words if word.isupper() and len(word) > 1)
        # Exclamation and question marks can indicate emotion
        exclamation_count = text.count("!")
        question_mark_count = text.count("?")

        return {
            "punctuation_count": punctuation_count,
            "punctuation_ratio": (punctuation_count / len(text)) if len(text) > 0 else 0,
            "uppercase_word_count": uppercase_word_count,
            "uppercase_word_ratio": (uppercase_word_count / len(words))
            if len(words) > 0
            else 0,
            "exclamation_mark_count": exclamation_count,
            "question_mark_count": question_mark_count,
        }

    def _word_shape_and_type_features(self, words: List[str]) -> Dict[str, Any]:
        """Extracts features based on word shape and type."""
        numeric_count = sum(1 for word in words if word.isdigit())
        # Words with all caps, often for emphasis
        all_caps_count = sum(1 for word in words if word.isupper() and len(word) > 1)

        return {
            "numeric_count": numeric_count,
            "all_caps_word_count": all_caps_count,
            "all_caps_word_ratio": (all_caps_count / len(words)) if len(words) > 0 else 0,
        }


# Singleton instance for efficient reuse
_feature_engineer_instance: Optional[FeatureEngineer] = None


def get_feature_engineer() -> FeatureEngineer:
    """Provides a singleton instance of the FeatureEngineer.

    This factory function ensures that the FeatureEngineer class, along with its
    NLTK resources, is initialized only once, promoting efficiency and
    preventing redundant resource loading.

    Returns:
        The singleton instance of the FeatureEngineer.
    """
    global _feature_engineer_instance
    if _feature_engineer_instance is None:
        logger.info("Initializing singleton FeatureEngineer instance...")
        _feature_engineer_instance = FeatureEngineer()
        logger.info("FeatureEngineer instance created successfully.")
    return _feature_engineer_instance
