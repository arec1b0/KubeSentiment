"""
Advanced Feature Engineering for Text Data.

This module provides a comprehensive suite of functions to extract a rich set
of features from raw text. These features can be used to enhance the
performance of machine learning models for sentiment analysis and other NLP
tasks by providing additional context beyond the raw text.
"""

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
    transforming raw text into a structured dictionary of numerical and
    categorical features. These features can provide valuable signals to a
    machine learning model, complementing the information learned from the
    text itself. The class also handles the download and setup of necessary
    NLTK resources.
    """

    def __init__(self, download_nltk_data: bool = True):
        """Initializes the FeatureEngineer and downloads NLTK data if needed.

        Args:
            download_nltk_data: If True, downloads required NLTK data on
                initialization. This should be set to False in environments
                where the data is pre-packaged or in testing scenarios.
        """
        if download_nltk_data:
            self._download_nltk_resources()

        self.lemmatizer = WordNetLemmatizer()
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words("english"))
        self.vader_analyzer = SentimentIntensityAnalyzer()

    def _download_nltk_resources(self) -> None:
        """Downloads all necessary NLTK resources for feature engineering.

        This method centralizes the downloading of NLTK data to ensure that
        all required components (e.g., tokenizers, lexicons) are available
        before any feature extraction is attempted. It is designed to be
        fault-tolerant, logging errors but not crashing if a download fails.
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
                    logger.error(f"Failed to download NLTK resource '{resource}': {e}")

    def extract_features(self, text: str) -> Dict[str, Any]:
        """Orchestrates the extraction of all features from a given text.

        This is the main public method of the class. It takes a raw text string
        and returns a dictionary of features by calling a series of private
        methods, each responsible for a different category of feature.

        Args:
            text: The input text to be processed.

        Returns:
            A dictionary containing a comprehensive set of extracted features.
            Returns an empty dictionary if the input text is invalid.
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

    def _text_statistics(self, text: str, words: List[str], sentences: List[str]) -> Dict[str, Any]:
        """Calculates basic statistical features of the text.

        These features provide a quantitative summary of the text's structure,
        such as its length in characters, words, and sentences.

        Args:
            text: The raw input text.
            words: A list of tokens (words) from the text.
            sentences: A list of sentences from the text.

        Returns:
            A dictionary of basic statistical features.
        """
        char_count = len(text)
        word_count = len(words)
        sentence_count = len(sentences)

        return {
            "char_count": char_count,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_word_length": (char_count / word_count) if word_count > 0 else 0,
            "avg_sentence_length": (word_count / sentence_count) if sentence_count > 0 else 0,
        }

    def _lexical_diversity(self, words: List[str]) -> Dict[str, Any]:
        """Calculates features related to the richness of the vocabulary.

        These features measure the variety of words used in the text, which
        can be an indicator of the text's complexity and style.

        Args:
            words: A list of tokens (words) from the text.

        Returns:
            A dictionary of features related to lexical diversity.
        """
        word_count = len(words)
        unique_word_count = len(set(words))
        stopwords_count = sum(1 for word in words if word in self.stop_words)

        return {
            "unique_word_count": unique_word_count,
            "lexical_richness": (unique_word_count / word_count) if word_count > 0 else 0,
            "stopwords_count": stopwords_count,
            "stopwords_ratio": (stopwords_count / word_count) if word_count > 0 else 0,
        }

    def _sentiment_scores(self, text: str) -> Dict[str, Any]:
        """Calculates VADER sentiment scores.

        VADER (Valence Aware Dictionary and sEntiment Reasoner) is a lexicon
        and rule-based sentiment analysis tool that is specifically attuned to
        sentiments expressed in social media.

        Args:
            text: The raw input text.

        Returns:
            A dictionary of VADER sentiment scores (compound, positive,
            negative, and neutral).
        """
        sentiment = self.vader_analyzer.polarity_scores(text)
        return {
            "vader_sentiment_compound": sentiment["compound"],
            "vader_sentiment_pos": sentiment["pos"],
            "vader_sentiment_neg": sentiment["neg"],
            "vader_sentiment_neu": sentiment["neu"],
        }

    def _readability_scores(self, text: str) -> Dict[str, Any]:
        """Calculates various readability metrics.

        These scores estimate the difficulty of understanding a passage of
        text. Different formulas are used, each providing a different
        perspective on readability.

        Args:
            text: The raw input text.

        Returns:
            A dictionary of various readability scores.
        """
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
        """Calculates features based on Part-of-Speech (POS) tagging.

        These features capture the grammatical structure of the text by
        counting the occurrences of different parts of speech (e.g., nouns,
        verbs, adjectives).

        Args:
            words: A list of tokens (words) from the text.

        Returns:
            A dictionary of features based on POS tags.
        """
        pos_counts = Counter(tag for word, tag in nltk.pos_tag(words))
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

    def _structural_and_stylistic_features(self, text: str, words: List[str]) -> Dict[str, Any]:
        """Extracts features related to text structure and writing style.

        These features capture aspects of the author's writing style, such as
        the use of punctuation and capitalization, which can be indicative of
        sentiment or tone.

        Args:
            text: The raw input text.
            words: A list of tokens (words) from the text.

        Returns:
            A dictionary of structural and stylistic features.
        """
        punctuation_count = sum(1 for char in text if char in string.punctuation)
        uppercase_word_count = sum(1 for word in words if word.isupper() and len(word) > 1)
        exclamation_count = text.count("!")
        question_mark_count = text.count("?")

        return {
            "punctuation_count": punctuation_count,
            "punctuation_ratio": (punctuation_count / len(text)) if text else 0,
            "uppercase_word_count": uppercase_word_count,
            "uppercase_word_ratio": (uppercase_word_count / len(words)) if words else 0,
            "exclamation_mark_count": exclamation_count,
            "question_mark_count": question_mark_count,
        }

    def _word_shape_and_type_features(self, words: List[str]) -> Dict[str, Any]:
        """Extracts features based on the shape and type of words.

        These features capture non-lexical aspects of the words, such as
        whether they are numeric or written in all caps, which can be useful
        for identifying emphasis or special content.

        Args:
            words: A list of tokens (words) from the text.

        Returns:
            A dictionary of features based on word shape and type.
        """
        numeric_count = sum(1 for word in words if word.isdigit())
        all_caps_count = sum(1 for word in words if word.isupper() and len(word) > 1)

        return {
            "numeric_count": numeric_count,
            "all_caps_word_count": all_caps_count,
            "all_caps_word_ratio": (all_caps_count / len(words)) if words else 0,
        }


_feature_engineer_instance: Optional[FeatureEngineer] = None


def get_feature_engineer(download_nltk_data: bool = True) -> FeatureEngineer:
    """Provides a singleton instance of the `FeatureEngineer`.

    This factory function ensures that the `FeatureEngineer` class, along with
    its potentially costly NLTK resource loading, is initialized only once.
    This singleton pattern promotes efficiency and prevents redundant
    initializations.

    Args:
        download_nltk_data: If True, downloads required NLTK data on
            initialization. Defaults to True.

    Returns:
        The singleton instance of the `FeatureEngineer`.
    """
    global _feature_engineer_instance
    if _feature_engineer_instance is None:
        logger.info("Initializing singleton FeatureEngineer instance...")
        _feature_engineer_instance = FeatureEngineer(download_nltk_data=download_nltk_data)
        logger.info("FeatureEngineer instance created successfully.")
    return _feature_engineer_instance
