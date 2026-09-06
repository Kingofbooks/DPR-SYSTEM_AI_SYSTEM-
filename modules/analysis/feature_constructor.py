import json
from pathlib import Path
from statistics import mean, pstdev


class FeatureConstructor:
    """
    Constructs machine-learning features from DPR completeness
    and quality assessment results.

    This module does NOT calculate completeness or quality.

    It only:
        1. Loads assessment results
        2. Extracts numerical values
        3. Normalizes them
        4. Creates derived features
        5. Saves the final feature vector

    The output is designed to be used later by a risk scoring model.
    """

    def __init__(self):
        print("Feature Constructor initialized.")

        self.processed_dir = Path("data/processed")

    # ============================================================
    # FILE LOADING
    # ============================================================

    def load_json(self, file_path):
        """
        Load a JSON file safely.
        """

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"\nFile not found:\n{file_path}"
            )

        try:
            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            return data

        except json.JSONDecodeError as error:

            raise ValueError(
                f"\nInvalid JSON file:\n"
                f"{file_path}\n"
                f"Error: {error}"
            )

    # ============================================================
    # VALUE NORMALIZATION
    # ============================================================

    @staticmethod
    def normalize_score(value):
        """
        Normalize a numerical score to the range:

            0.0 -> 1.0

        Supports both:

            0.875
            87.5

        Invalid values return None.
        """

        if value is None:
            return None

        try:

            value = float(value)

        except (TypeError, ValueError):

            return None

        # Convert percentages to decimals.
        if value > 1.0:
            value = value / 100.0

        # Clamp to valid range.
        value = max(
            0.0,
            min(value, 1.0)
        )

        return round(value, 6)

    # ============================================================
    # RECURSIVE VALUE FINDER
    # ============================================================

    @staticmethod
    def find_value(data, possible_keys):
        """
        Search recursively through a JSON dictionary
        for the first matching key.

        Example:

        possible_keys = [
            "completeness_score",
            "completeness",
            "score"
        ]

        Returns:
            value or None
        """

        if isinstance(data, dict):

            # First check current level.
            for key in possible_keys:

                if key in data:
                    return data[key]

            # Search nested dictionaries.
            for value in data.values():

                result = FeatureConstructor.find_value(
                    value,
                    possible_keys
                )

                if result is not None:
                    return result

        elif isinstance(data, list):

            # Search each item.
            for item in data:

                result = FeatureConstructor.find_value(
                    item,
                    possible_keys
                )

                if result is not None:
                    return result

        return None

    # ============================================================
    # EXTRACT ALL VALUES FOR A KEY
    # ============================================================

    @staticmethod
    def find_all_values(data, possible_keys):
        """
        Recursively collect ALL numerical values matching
        the provided keys.

        Useful for section quality scores.
        """

        values = []

        if isinstance(data, dict):

            for key, value in data.items():

                if key in possible_keys:

                    try:

                        values.append(
                            float(value)
                        )

                    except (
                        TypeError,
                        ValueError
                    ):
                        pass

                # Continue recursive search.
                values.extend(
                    FeatureConstructor.find_all_values(
                        value,
                        possible_keys
                    )
                )

        elif isinstance(data, list):

            for item in data:

                values.extend(
                    FeatureConstructor.find_all_values(
                        item,
                        possible_keys
                    )
                )

        return values

    # ============================================================
    # DOCUMENT NAME EXTRACTION
    # ============================================================

    def get_document_name(
        self,
        completeness_data,
        quality_data,
        fallback_name
    ):
        """
        Extract document filename dynamically.
        """

        possible_keys = [
            "filename",
            "document_name",
            "document",
            "source_file"
        ]

        document_name = self.find_value(
            completeness_data,
            possible_keys
        )

        if document_name is None:

            document_name = self.find_value(
                quality_data,
                possible_keys
            )

        if document_name is None:

            document_name = fallback_name

        return str(document_name)

    # ============================================================
    # COMPLETENESS FEATURE EXTRACTION
    # ============================================================

    def extract_completeness_features(
        self,
        completeness_data
    ):
        """
        Extract completeness-related features.

        Supports different JSON structures and key names.
        """

        print(
            "\nExtracting completeness features..."
        )

        completeness_score = self.find_value(
            completeness_data,
            [
                "completeness_score",
                "completeness"
            ]
        )

        critical_completeness = self.find_value(
            completeness_data,
            [
                "critical_completeness",
                "critical_completeness_score"
            ]
        )

        weighted_completeness = self.find_value(
            completeness_data,
            [
                "weighted_completeness",
                "weighted_score",
                "weighted_completeness_score"
            ]
        )

        expected_sections = self.find_value(
            completeness_data,
            [
                "expected_sections",
                "total_expected_sections"
            ]
        )

        found_sections = self.find_value(
            completeness_data,
            [
                "found_sections",
                "found_section_count"
            ]
        )

        missing_sections = self.find_value(
            completeness_data,
            [
                "missing_sections",
                "missing_section_count"
            ]
        )

        critical_missing_sections = self.find_value(
            completeness_data,
            [
                "critical_missing_sections",
                "critical_missing_count"
            ]
        )

        # --------------------------------------------------------
        # NORMALIZE SCORES
        # --------------------------------------------------------

        completeness_score = (
            self.normalize_score(
                completeness_score
            )
        )

        critical_completeness = (
            self.normalize_score(
                critical_completeness
            )
        )

        weighted_completeness = (
            self.normalize_score(
                weighted_completeness
            )
        )

        # --------------------------------------------------------
        # SAFE NUMERIC CONVERSION
        # --------------------------------------------------------

        try:
            expected_sections = int(
                expected_sections
            )
        except (
            TypeError,
            ValueError
        ):
            expected_sections = 0

        try:
            found_sections = int(
                found_sections
            )
        except (
            TypeError,
            ValueError
        ):
            found_sections = 0

        try:
            missing_sections = int(
                missing_sections
            )
        except (
            TypeError,
            ValueError
        ):
            missing_sections = 0

        try:
            critical_missing_sections = int(
                critical_missing_sections
            )
        except (
            TypeError,
            ValueError
        ):
            critical_missing_sections = 0

        # --------------------------------------------------------
        # DERIVED RATIOS
        # --------------------------------------------------------

        if expected_sections > 0:

            found_section_ratio = (
                found_sections /
                expected_sections
            )

            missing_section_ratio = (
                missing_sections /
                expected_sections
            )

            critical_missing_ratio = (
                critical_missing_sections /
                expected_sections
            )

        else:

            found_section_ratio = 0.0
            missing_section_ratio = 0.0
            critical_missing_ratio = 0.0

        # --------------------------------------------------------
        # FALLBACK COMPLETENESS
        #
        # If score key isn't found but counts exist,
        # calculate it dynamically.
        # --------------------------------------------------------

        if (
            completeness_score is None
            and expected_sections > 0
        ):

            completeness_score = (
                found_sections /
                expected_sections
            )

        # --------------------------------------------------------
        # FINAL FALLBACKS
        # --------------------------------------------------------

        if completeness_score is None:
            completeness_score = 0.0

        if critical_completeness is None:
            critical_completeness = 0.0

        if weighted_completeness is None:
            weighted_completeness = (
                completeness_score
            )

        features = {

            "completeness_score":
                round(
                    completeness_score,
                    6
                ),

            "critical_completeness":
                round(
                    critical_completeness,
                    6
                ),

            "weighted_completeness":
                round(
                    weighted_completeness,
                    6
                ),

            "found_section_ratio":
                round(
                    found_section_ratio,
                    6
                ),

            "missing_section_ratio":
                round(
                    missing_section_ratio,
                    6
                ),

            "critical_missing_ratio":
                round(
                    critical_missing_ratio,
                    6
                )
        }

        return features

    # ============================================================
    # QUALITY FEATURE EXTRACTION
    # ============================================================

    def extract_quality_features(
        self,
        quality_data
    ):
        """
        Extract document-level quality features.
        """

        print(
            "Extracting quality features..."
        )

        document_quality = self.find_value(
            quality_data,
            [
                "document_quality_score",
                "document_quality",
                "quality_score"
            ]
        )

        average_section_quality = self.find_value(
            quality_data,
            [
                "average_section_quality",
                "average_quality"
            ]
        )

        weak_sections = self.find_value(
            quality_data,
            [
                "weak_sections",
                "weak_section_count"
            ]
        )

        total_sections = self.find_value(
            quality_data,
            [
                "total_sections",
                "section_count"
            ]
        )

        # --------------------------------------------------------
        # NORMALIZE SCORES
        # --------------------------------------------------------

        document_quality = (
            self.normalize_score(
                document_quality
            )
        )

        average_section_quality = (
            self.normalize_score(
                average_section_quality
            )
        )

        # --------------------------------------------------------
        # SAFE SECTION COUNTS
        # --------------------------------------------------------

        try:
            total_sections = int(
                total_sections
            )
        except (
            TypeError,
            ValueError
        ):
            total_sections = 0

        # weak_sections may be:
        #
        # 1. Integer
        # 2. List of weak sections
        #

        if isinstance(
            weak_sections,
            list
        ):

            weak_section_count = len(
                weak_sections
            )

        else:

            try:

                weak_section_count = int(
                    weak_sections
                )

            except (
                TypeError,
                ValueError
            ):

                weak_section_count = 0

        # --------------------------------------------------------
        # WEAK SECTION RATIO
        # --------------------------------------------------------

        if total_sections > 0:

            weak_section_ratio = (
                weak_section_count /
                total_sections
            )

        else:

            weak_section_ratio = 0.0

        # --------------------------------------------------------
        # FALLBACKS
        # --------------------------------------------------------

        if document_quality is None:
            document_quality = 0.0

        if average_section_quality is None:
            average_section_quality = (
                document_quality
            )

        features = {

            "document_quality_score":
                round(
                    document_quality,
                    6
                ),

            "average_section_quality":
                round(
                    average_section_quality,
                    6
                ),

            "weak_section_ratio":
                round(
                    weak_section_ratio,
                    6
                )
        }

        return features

    # ============================================================
    # SECTION QUALITY EXTRACTION
    # ============================================================

    def extract_section_quality_scores(
        self,
        quality_data
    ):
        """
        Extract individual section quality scores.

        First checks for common structures such as:

        section_results
        section_scores
        sections

        Returns a clean list of normalized scores.
        """

        print(
            "Extracting section quality statistics..."
        )

        possible_containers = [

            "section_results",

            "section_scores",

            "sections",

            "section_quality_results"

        ]

        section_container = None

        for key in possible_containers:

            if (
                isinstance(
                    quality_data,
                    dict
                )
                and key in quality_data
            ):

                section_container = (
                    quality_data[key]
                )

                break

        scores = []

        # --------------------------------------------------------
        # CASE 1:
        #
        # A list of section dictionaries.
        # --------------------------------------------------------

        if isinstance(
            section_container,
            list
        ):

            for item in section_container:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                score = self.find_value(
                    item,
                    [
                        "quality_score",
                        "score",
                        "section_quality"
                    ]
                )

                score = self.normalize_score(
                    score
                )

                if score is not None:

                    scores.append(score)

        # --------------------------------------------------------
        # CASE 2:
        #
        # A dictionary of sections.
        # --------------------------------------------------------

        elif isinstance(
            section_container,
            dict
        ):

            for value in (
                section_container.values()
            ):

                if isinstance(
                    value,
                    dict
                ):

                    score = self.find_value(
                        value,
                        [
                            "quality_score",
                            "score",
                            "section_quality"
                        ]
                    )

                    score = self.normalize_score(
                        score
                    )

                    if score is not None:

                        scores.append(score)

                else:

                    score = self.normalize_score(
                        value
                    )

                    if score is not None:

                        scores.append(score)

        # --------------------------------------------------------
        # FALLBACK:
        #
        # Search the entire JSON.
        #
        # We only use quality_score and section_quality
        # to avoid accidentally collecting document-level
        # summary scores.
        # --------------------------------------------------------

        if not scores:

            all_scores = (
                self.find_all_values(
                    quality_data,
                    [
                        "quality_score",
                        "section_quality"
                    ]
                )
            )

            for score in all_scores:

                normalized_score = (
                    self.normalize_score(
                        score
                    )
                )

                if normalized_score is not None:

                    scores.append(
                        normalized_score
                    )

        return scores

    # ============================================================
    # SECTION QUALITY STATISTICS
    # ============================================================

    def calculate_section_statistics(
        self,
        scores
    ):
        """
        Calculate statistical features from
        section quality scores.
        """

        if not scores:

            return {

                "excellent_section_ratio": 0.0,

                "min_section_quality": 0.0,

                "max_section_quality": 0.0,

                "section_quality_range": 0.0,

                "section_quality_std_proxy": 0.0
            }

        # --------------------------------------------------------
        # EXCELLENT SECTION RATIO
        #
        # This is based on the actual score values.
        # --------------------------------------------------------

        excellent_sections = sum(

            1

            for score in scores

            if score >= 0.85
        )

        excellent_section_ratio = (

            excellent_sections /
            len(scores)

        )

        # --------------------------------------------------------
        # STANDARD DEVIATION
        # --------------------------------------------------------

        if len(scores) > 1:

            standard_deviation = pstdev(
                scores
            )

        else:

            standard_deviation = 0.0

        features = {

            "excellent_section_ratio":

                round(
                    excellent_section_ratio,
                    6
                ),

            "min_section_quality":

                round(
                    min(scores),
                    6
                ),

            "max_section_quality":

                round(
                    max(scores),
                    6
                ),

            "section_quality_range":

                round(
                    max(scores)
                    -
                    min(scores),
                    6
                ),

            "section_quality_std_proxy":

                round(
                    standard_deviation,
                    6
                )
        }

        return features

    # ============================================================
    # DERIVED FEATURES
    # ============================================================

    def construct_derived_features(
        self,
        features
    ):
        """
        Construct higher-level features from
        completeness and quality metrics.

        These features are NOT hardcoded DPR values.

        They are calculated dynamically from
        assessment results.
        """

        completeness = features.get(
            "weighted_completeness",
            0.0
        )

        quality = features.get(
            "document_quality_score",
            0.0
        )

        # --------------------------------------------------------
        # OVERALL DOCUMENT HEALTH
        #
        # Equal contribution:
        #
        # Completeness = 50%
        # Quality = 50%
        #
        # This is a feature engineering decision,
        # not a document-specific hardcoded value.
        # --------------------------------------------------------

        overall_document_health = (

            (
                completeness
                +
                quality
            )
            /
            2
        )

        # --------------------------------------------------------
        # COMPLETENESS / QUALITY GAP
        #
        # A large gap can indicate inconsistency.
        # --------------------------------------------------------

        completeness_quality_gap = abs(

            completeness
            -
            quality

        )

        # --------------------------------------------------------
        # DOCUMENT WEAKNESS SCORE
        #
        # Higher value = weaker document.
        #
        # Derived dynamically.
        # --------------------------------------------------------

        document_weakness_score = (

            1.0
            -
            overall_document_health

        )

        derived_features = {

            "overall_document_health":

                round(
                    overall_document_health,
                    6
                ),

            "completeness_quality_gap":

                round(
                    completeness_quality_gap,
                    6
                ),

            "document_weakness_score":

                round(
                    document_weakness_score,
                    6
                )
        }

        return derived_features

    # ============================================================
    # MAIN FEATURE CONSTRUCTION
    # ============================================================

    def construct_features(
        self,
        completeness_file,
        quality_file
    ):
        """
        Main feature construction pipeline.
        """

        print(
            "\n"
            +
            "=" * 60
        )

        print(
            "CONSTRUCTING DPR FEATURES"
        )

        print(
            "=" * 60
        )

        # --------------------------------------------------------
        # LOAD FILES
        # --------------------------------------------------------

        completeness_data = self.load_json(
            completeness_file
        )

        quality_data = self.load_json(
            quality_file
        )

        # --------------------------------------------------------
        # EXTRACT DOCUMENT NAME
        # --------------------------------------------------------

        fallback_name = (
            Path(completeness_file)
            .stem
            .replace(
                "_completeness",
                ""
            )
        )

        document_name = (
            self.get_document_name(
                completeness_data,
                quality_data,
                fallback_name
            )
        )

        # --------------------------------------------------------
        # COMPLETENESS FEATURES
        # --------------------------------------------------------

        completeness_features = (

            self.extract_completeness_features(
                completeness_data
            )

        )

        # --------------------------------------------------------
        # QUALITY FEATURES
        # --------------------------------------------------------

        quality_features = (

            self.extract_quality_features(
                quality_data
            )

        )

        # --------------------------------------------------------
        # SECTION QUALITY FEATURES
        # --------------------------------------------------------

        section_scores = (

            self.extract_section_quality_scores(
                quality_data
            )

        )

        section_statistics = (

            self.calculate_section_statistics(
                section_scores
            )

        )

        # --------------------------------------------------------
        # COMBINE BASE FEATURES
        # --------------------------------------------------------

        features = {}

        features.update(
            completeness_features
        )

        features.update(
            quality_features
        )

        features.update(
            section_statistics
        )

        # --------------------------------------------------------
        # DERIVED FEATURES
        # --------------------------------------------------------

        derived_features = (

            self.construct_derived_features(
                features
            )

        )

        features.update(
            derived_features
        )

        # --------------------------------------------------------
        # FINAL RESULT
        # --------------------------------------------------------

        result = {

            "document": document_name,

            "feature_count":
                len(features),

            "features":
                features
        }

        print(
            f"\nTotal Features: "
            f"{len(features)}"
        )

        return result

    # ============================================================
    # SAVE FEATURES
    # ============================================================

    def save_features(
        self,
        result,
        output_path
    ):
        """
        Save constructed features to JSON.
        """

        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                result,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(
            "\nFeatures saved successfully:"
        )

        print(
            output_path
        )


# ============================================================
# TEST PIPELINE
# ============================================================

def main():

    print(
        "\n"
        +
        "=" * 60
    )

    print(
        "STARTING DPR FEATURE CONSTRUCTION"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # FILE PATHS
    # --------------------------------------------------------

    completeness_file = Path(
        "data/processed/"
        "DPR of Road_completeness.json"
    )

    quality_file = Path(
        "data/processed/"
        "DPR of Road_quality.json"
    )

    output_file = Path(
        "data/processed/"
        "DPR of Road_features.json"
    )

    # --------------------------------------------------------
    # INITIALIZE
    # --------------------------------------------------------

    constructor = FeatureConstructor()

    print(
        "\nLoading assessment files..."
    )

    print(
        f"Loaded: "
        f"{completeness_file.name}"
    )

    print(
        f"Loaded: "
        f"{quality_file.name}"
    )

    # --------------------------------------------------------
    # CONSTRUCT FEATURES
    # --------------------------------------------------------

    result = (
        constructor.construct_features(

            completeness_file=
                completeness_file,

            quality_file=
                quality_file
        )
    )

    # --------------------------------------------------------
    # SAVE FEATURES
    # --------------------------------------------------------

    constructor.save_features(

        result=result,

        output_path=output_file
    )

    # --------------------------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------------------------

    print(
        "\n"
        +
        "=" * 60
    )

    print(
        "FEATURE CONSTRUCTION COMPLETE"
    )

    print(
        "=" * 60
    )

    print(
        f"\nDocument: "
        f"{result['document']}"
    )

    print(
        f"Feature Count: "
        f"{result['feature_count']}"
    )

    print(
        "\nFEATURES"
    )

    print(
        "-" * 60
    )

    for (
        feature_name,
        feature_value
    ) in (
        result["features"]
        .items()
    ):

        print(
            f"{feature_name}: "
            f"{feature_value}"
        )

    print(
        "\n"
        +
        "=" * 60
    )

    print(
        "DONE"
    )

    print(
        "=" * 60
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()