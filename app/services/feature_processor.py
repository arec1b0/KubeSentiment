"""Feature processing utilities for stream processing."""

from typing import Any, List

import pandas as pd


class FeatureProcessor:
    """Handles feature extraction and normalization for batch processing."""

    # List of numerical features to extract and normalize
    NUMERICAL_FEATURES = [
        "char_count",
        "word_count",
        "sentence_count",
        "avg_word_length",
        "avg_sentence_length",
        "unique_word_count",
        "lexical_richness",
        "stopwords_count",
        "stopwords_ratio",
        "vader_sentiment_compound",
        "vader_sentiment_pos",
        "vader_sentiment_neg",
        "vader_sentiment_neu",
        "flesch_reading_ease",
        "flesch_kincaid_grade",
        "smog_index",
        "coleman_liau_index",
        "automated_readability_index",
        "dale_chall_readability_score",
        "gunning_fog",
        "noun_count",
        "verb_count",
        "adjective_count",
        "adverb_count",
        "pronoun_count",
        "noun_ratio",
        "verb_ratio",
        "adjective_ratio",
        "punctuation_count",
        "punctuation_ratio",
        "uppercase_word_count",
        "uppercase_word_ratio",
        "exclamation_mark_count",
        "question_mark_count",
        "numeric_count",
        "all_caps_word_count",
        "all_caps_word_ratio",
    ]

    @staticmethod
    def process_features(
        texts: List[str], feature_engineer: Any, online_scaler: Any, batch_logger: Any
    ) -> None:
        """Processes and normalizes features for a batch of texts.

        This method extracts numerical features from the texts, updates the
        online scaler with the new data, and then normalizes the features
        before prediction.

        Args:
            texts: A list of input texts for feature extraction.
            feature_engineer: The feature engineering instance.
            online_scaler: The online normalization scaler.
            batch_logger: A contextual logger for logging batch-specific information.
        """
        try:
            feature_dicts = [
                feature_engineer.extract_features(text) for text in texts
            ]
            feature_df = pd.DataFrame(feature_dicts).fillna(0)

            available_features = [
                col for col in FeatureProcessor.NUMERICAL_FEATURES if col in feature_df.columns
            ]
            feature_array = feature_df[available_features].values

            if feature_array.shape[0] > 0:
                online_scaler.partial_fit(feature_array)
                normalized_features = online_scaler.transform(feature_array)
                batch_logger.info(
                    "Normalized features generated",
                    shape=normalized_features.shape,
                    n_features=len(available_features),
                    scaler_samples_seen=online_scaler.n_samples_seen_,
                )
            else:
                batch_logger.warning(
                    "No numerical features available for normalization"
                )
        except Exception as fe_e:
            batch_logger.error(
                "Feature engineering/normalization failed",
                error=str(fe_e),
                exc_info=True,
            )
