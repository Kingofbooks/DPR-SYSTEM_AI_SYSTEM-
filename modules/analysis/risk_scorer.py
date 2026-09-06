import json
from pathlib import Path


class RiskScorer:
    """
    DPR Risk Scoring Engine.

    This module converts constructed DPR features into:

    - Risk score
    - Risk level
    - Risk component scores
    - Risk factors
    - Positive factors

    NOTE:
    This is currently an explainable rule-based scoring system.

    It is intentionally separated from the rest of the pipeline so
    it can later be replaced with a trained ML model.
    """

    def __init__(self):
        print("Risk Scorer initialized.")

    # ============================================================
    # FILE LOADING
    # ============================================================

    def load_features(self, file_path):
        """
        Load DPR feature file.
        """

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Feature file not found: {file_path}"
            )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        print("\nFeatures loaded successfully.")

        return data

    # ============================================================
    # SAFE FEATURE EXTRACTION
    # ============================================================

    @staticmethod
    def get_feature(features, name, default=0.0):
        """
        Safely extract a numeric feature.
        """

        value = features.get(name, default)

        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    # ============================================================
    # NORMALIZATION
    # ============================================================

    @staticmethod
    def clamp(value, minimum=0.0, maximum=1.0):
        """
        Ensure value remains within a range.
        """

        return max(
            minimum,
            min(maximum, value)
        )

    # ============================================================
    # COMPLETENESS RISK
    # ============================================================

    def calculate_completeness_risk(self, features):
        """
        Calculate risk caused by incomplete DPR information.

        Higher completeness = lower risk.
        """

        completeness = self.get_feature(
            features,
            "weighted_completeness"
        )

        critical_completeness = self.get_feature(
            features,
            "critical_completeness"
        )

        missing_ratio = self.get_feature(
            features,
            "missing_section_ratio"
        )

        critical_missing_ratio = self.get_feature(
            features,
            "critical_missing_ratio"
        )

        completeness_risk = 1.0 - completeness

        critical_risk = (
            1.0 - critical_completeness
        )

        missing_risk = missing_ratio

        critical_missing_risk = (
            critical_missing_ratio
        )

        risk = (
            completeness_risk * 0.40
            + critical_risk * 0.30
            + missing_risk * 0.15
            + critical_missing_risk * 0.15
        )

        return self.clamp(risk)

    # ============================================================
    # QUALITY RISK
    # ============================================================

    def calculate_quality_risk(self, features):
        """
        Calculate risk caused by poor document quality.
        """

        document_quality = self.get_feature(
            features,
            "document_quality_score"
        )

        average_quality = self.get_feature(
            features,
            "average_section_quality"
        )

        minimum_quality = self.get_feature(
            features,
            "min_section_quality"
        )

        document_quality_risk = (
            1.0 - document_quality
        )

        average_quality_risk = (
            1.0 - average_quality
        )

        minimum_quality_risk = (
            1.0 - minimum_quality
        )

        risk = (
            document_quality_risk * 0.45
            + average_quality_risk * 0.35
            + minimum_quality_risk * 0.20
        )

        return self.clamp(risk)

    # ============================================================
    # DOCUMENT HEALTH RISK
    # ============================================================

    def calculate_health_risk(self, features):
        """
        Calculate risk based on overall document health.
        """

        document_health = self.get_feature(
            features,
            "overall_document_health"
        )

        health_risk = 1.0 - document_health

        return self.clamp(health_risk)

    # ============================================================
    # DOCUMENT WEAKNESS RISK
    # ============================================================

    def calculate_weakness_risk(self, features):
        """
        Calculate risk caused by weak document areas.
        """

        weakness_score = self.get_feature(
            features,
            "document_weakness_score"
        )

        weak_section_ratio = self.get_feature(
            features,
            "weak_section_ratio"
        )

        risk = (
            weakness_score * 0.70
            + weak_section_ratio * 0.30
        )

        return self.clamp(risk)

    # ============================================================
    # SECTION CONSISTENCY RISK
    # ============================================================

    def calculate_consistency_risk(self, features):
        """
        Measure variation in section quality.

        Large variation can indicate inconsistent document quality.
        """

        quality_range = self.get_feature(
            features,
            "section_quality_range"
        )

        quality_std = self.get_feature(
            features,
            "section_quality_std_proxy"
        )

        risk = (
            quality_range * 0.60
            + quality_std * 0.40
        )

        return self.clamp(risk)

    # ============================================================
    # FINAL RISK SCORE
    # ============================================================

    def calculate_final_risk(
        self,
        completeness_risk,
        quality_risk,
        health_risk,
        weakness_risk,
        consistency_risk
    ):
        """
        Combine all risk dimensions.
        """

        final_risk = (
            completeness_risk * 0.35
            + quality_risk * 0.25
            + health_risk * 0.20
            + weakness_risk * 0.10
            + consistency_risk * 0.10
        )

        return self.clamp(final_risk)

    # ============================================================
    # RISK LEVEL
    # ============================================================

    @staticmethod
    def get_risk_level(risk_score):
        """
        Convert numerical risk score into a risk category.
        """

        if risk_score < 0.25:
            return "LOW"

        elif risk_score < 0.50:
            return "MEDIUM"

        elif risk_score < 0.75:
            return "HIGH"

        return "CRITICAL"

    # ============================================================
    # RISK FACTORS
    # ============================================================

    def identify_risk_factors(
        self,
        features,
        component_scores
    ):
        """
        Identify important contributors to DPR risk.
        """

        risk_factors = []

        weighted_completeness = self.get_feature(
            features,
            "weighted_completeness"
        )

        critical_completeness = self.get_feature(
            features,
            "critical_completeness"
        )

        document_quality = self.get_feature(
            features,
            "document_quality_score"
        )

        average_quality = self.get_feature(
            features,
            "average_section_quality"
        )

        min_quality = self.get_feature(
            features,
            "min_section_quality"
        )

        document_health = self.get_feature(
            features,
            "overall_document_health"
        )

        weakness_score = self.get_feature(
            features,
            "document_weakness_score"
        )

        weak_section_ratio = self.get_feature(
            features,
            "weak_section_ratio"
        )

        # --------------------------------------------------------
        # COMPLETENESS
        # --------------------------------------------------------

        if weighted_completeness < 0.75:
            risk_factors.append({
                "factor": "Low document completeness",
                "value": round(weighted_completeness, 4),
                "severity": "HIGH"
            })

        elif weighted_completeness < 0.90:
            risk_factors.append({
                "factor": "Document completeness could be improved",
                "value": round(weighted_completeness, 4),
                "severity": "MEDIUM"
            })

        # --------------------------------------------------------
        # CRITICAL COMPLETENESS
        # --------------------------------------------------------

        if critical_completeness < 0.90:

            risk_factors.append({
                "factor": "Critical DPR components may be missing",
                "value": round(critical_completeness, 4),
                "severity": "HIGH"
            })

        # --------------------------------------------------------
        # DOCUMENT QUALITY
        # --------------------------------------------------------

        if document_quality < 0.70:

            risk_factors.append({
                "factor": "Low overall document quality",
                "value": round(document_quality, 4),
                "severity": "HIGH"
            })

        elif document_quality < 0.85:

            risk_factors.append({
                "factor": "Document quality needs improvement",
                "value": round(document_quality, 4),
                "severity": "MEDIUM"
            })

        # --------------------------------------------------------
        # AVERAGE QUALITY
        # --------------------------------------------------------

        if average_quality < 0.70:

            risk_factors.append({
                "factor": "Low average section quality",
                "value": round(average_quality, 4),
                "severity": "HIGH"
            })

        # --------------------------------------------------------
        # MINIMUM SECTION QUALITY
        # --------------------------------------------------------

        if min_quality < 0.60:

            risk_factors.append({
                "factor": "At least one section has poor quality",
                "value": round(min_quality, 4),
                "severity": "HIGH"
            })

        elif min_quality < 0.75:

            risk_factors.append({
                "factor": "At least one section has moderate quality",
                "value": round(min_quality, 4),
                "severity": "MEDIUM"
            })

        # --------------------------------------------------------
        # DOCUMENT HEALTH
        # --------------------------------------------------------

        if document_health < 0.70:

            risk_factors.append({
                "factor": "Low overall document health",
                "value": round(document_health, 4),
                "severity": "HIGH"
            })

        elif document_health < 0.85:

            risk_factors.append({
                "factor": "Document health could be improved",
                "value": round(document_health, 4),
                "severity": "MEDIUM"
            })

        # --------------------------------------------------------
        # WEAKNESS SCORE
        # --------------------------------------------------------

        if weakness_score > 0.50:

            risk_factors.append({
                "factor": "High document weakness score",
                "value": round(weakness_score, 4),
                "severity": "HIGH"
            })

        elif weakness_score > 0.25:

            risk_factors.append({
                "factor": "Moderate document weakness",
                "value": round(weakness_score, 4),
                "severity": "MEDIUM"
            })

        # --------------------------------------------------------
        # WEAK SECTIONS
        # --------------------------------------------------------

        if weak_section_ratio > 0.30:

            risk_factors.append({
                "factor": "High number of weak sections",
                "value": round(weak_section_ratio, 4),
                "severity": "HIGH"
            })

        elif weak_section_ratio > 0.10:

            risk_factors.append({
                "factor": "Some sections have weak quality",
                "value": round(weak_section_ratio, 4),
                "severity": "MEDIUM"
            })

        # --------------------------------------------------------
        # COMPONENT RISKS
        # --------------------------------------------------------

        for component, score in component_scores.items():

            if score >= 0.60:

                risk_factors.append({
                    "factor": f"High {component.replace('_', ' ')} risk",
                    "value": round(score, 4),
                    "severity": "HIGH"
                })

            elif score >= 0.40:

                risk_factors.append({
                    "factor": f"Moderate {component.replace('_', ' ')} risk",
                    "value": round(score, 4),
                    "severity": "MEDIUM"
                })

        return risk_factors

    # ============================================================
    # POSITIVE FACTORS
    # ============================================================

    def identify_positive_factors(self, features):
        """
        Identify strengths of the DPR.
        """

        positive_factors = []

        weighted_completeness = self.get_feature(
            features,
            "weighted_completeness"
        )

        document_quality = self.get_feature(
            features,
            "document_quality_score"
        )

        document_health = self.get_feature(
            features,
            "overall_document_health"
        )

        excellent_section_ratio = self.get_feature(
            features,
            "excellent_section_ratio"
        )

        weak_section_ratio = self.get_feature(
            features,
            "weak_section_ratio"
        )

        if weighted_completeness >= 0.90:

            positive_factors.append(
                "High document completeness"
            )

        if document_quality >= 0.85:

            positive_factors.append(
                "Strong overall document quality"
            )

        if document_health >= 0.85:

            positive_factors.append(
                "Strong overall document health"
            )

        if excellent_section_ratio >= 0.50:

            positive_factors.append(
                "Majority of sections have excellent quality"
            )

        if weak_section_ratio == 0:

            positive_factors.append(
                "No weak sections detected"
            )

        return positive_factors

    # ============================================================
    # MAIN RISK ASSESSMENT
    # ============================================================

    def assess(self, feature_data):
        """
        Perform complete DPR risk assessment.
        """

        print("\nAssessing DPR risk...")

        # --------------------------------------------------------
        # SUPPORT BOTH STRUCTURES
        # --------------------------------------------------------

        if "features" in feature_data:

            features = feature_data["features"]

        else:

            features = feature_data

        metadata = feature_data.get(
            "metadata",
            {}
        )

        document_name = metadata.get(
            "filename",
            feature_data.get(
                "filename",
                "Unknown Document"
            )
        )

        print(
            f"Document: {document_name}"
        )

        # --------------------------------------------------------
        # COMPONENT RISKS
        # --------------------------------------------------------

        print(
            "\nCalculating risk components..."
        )

        completeness_risk = (
            self.calculate_completeness_risk(
                features
            )
        )

        quality_risk = (
            self.calculate_quality_risk(
                features
            )
        )

        health_risk = (
            self.calculate_health_risk(
                features
            )
        )

        weakness_risk = (
            self.calculate_weakness_risk(
                features
            )
        )

        consistency_risk = (
            self.calculate_consistency_risk(
                features
            )
        )

        component_scores = {

            "completeness_risk":
                completeness_risk,

            "quality_risk":
                quality_risk,

            "health_risk":
                health_risk,

            "weakness_risk":
                weakness_risk,

            "consistency_risk":
                consistency_risk
        }

        # --------------------------------------------------------
        # FINAL SCORE
        # --------------------------------------------------------

        print(
            "Calculating final risk score..."
        )

        final_risk = (
            self.calculate_final_risk(
                completeness_risk,
                quality_risk,
                health_risk,
                weakness_risk,
                consistency_risk
            )
        )

        risk_level = self.get_risk_level(
            final_risk
        )

        # --------------------------------------------------------
        # FACTORS
        # --------------------------------------------------------

        print(
            "Identifying risk factors..."
        )

        risk_factors = (
            self.identify_risk_factors(
                features,
                component_scores
            )
        )

        positive_factors = (
            self.identify_positive_factors(
                features
            )
        )

        # --------------------------------------------------------
        # RESULT
        # --------------------------------------------------------

        result = {

            "metadata": {

                "filename": document_name

            },

            "risk_assessment": {

                "risk_score":
                    round(final_risk, 4),

                "risk_percentage":
                    round(final_risk * 100, 2),

                "risk_level":
                    risk_level,

                "component_risks": {

                    key:
                    round(value, 4)

                    for key, value in
                    component_scores.items()

                },

                "risk_factors":
                    risk_factors,

                "positive_factors":
                    positive_factors

            }

        }

        return result

    # ============================================================
    # SAVE RESULT
    # ============================================================

    def save_result(
        self,
        result,
        output_path
    ):
        """
        Save risk assessment.
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
            "\nRisk assessment saved successfully:"
        )

        print(output_path)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "\n"
        + "=" * 60
    )

    print(
        "STARTING DPR RISK SCORING"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # PATHS
    # --------------------------------------------------------

    input_path = Path(
        "data/processed/DPR of Road_features.json"
    )

    output_path = Path(
        "data/processed/DPR of Road_risk.json"
    )

    # --------------------------------------------------------
    # INITIALIZE
    # --------------------------------------------------------

    scorer = RiskScorer()

    # --------------------------------------------------------
    # LOAD FEATURES
    # --------------------------------------------------------

    print(
        "\nLoading DPR features..."
    )

    feature_data = (
        scorer.load_features(
            input_path
        )
    )

    # --------------------------------------------------------
    # ASSESS RISK
    # --------------------------------------------------------

    result = scorer.assess(
        feature_data
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    scorer.save_result(
        result,
        output_path
    )

    # --------------------------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------------------------

    assessment = (
        result["risk_assessment"]
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "DPR RISK ASSESSMENT COMPLETE"
    )

    print(
        "=" * 60
    )

    print(
        f"\nDocument: "
        f"{result['metadata']['filename']}"
    )

    print(
        f"\nRisk Score: "
        f"{assessment['risk_score']}"
    )

    print(
        f"Risk Percentage: "
        f"{assessment['risk_percentage']}%"
    )

    print(
        f"Risk Level: "
        f"{assessment['risk_level']}"
    )

    # --------------------------------------------------------
    # COMPONENT RISKS
    # --------------------------------------------------------

    print(
        "\nCOMPONENT RISKS"
    )

    print(
        "-" * 60
    )

    for component, score in (
        assessment[
            "component_risks"
        ].items()
    ):

        print(
            f"{component}: "
            f"{round(score * 100, 2)}%"
        )

    # --------------------------------------------------------
    # RISK FACTORS
    # --------------------------------------------------------

    print(
        "\nRISK FACTORS"
    )

    print(
        "-" * 60
    )

    if assessment["risk_factors"]:

        for factor in (
            assessment["risk_factors"]
        ):

            print(
                f"[{factor['severity']}] "
                f"{factor['factor']} "
                f"({factor['value']})"
            )

    else:

        print(
            "No significant risk factors detected."
        )

    # --------------------------------------------------------
    # POSITIVE FACTORS
    # --------------------------------------------------------

    print(
        "\nPOSITIVE FACTORS"
    )

    print(
        "-" * 60
    )

    if assessment["positive_factors"]:

        for factor in (
            assessment[
                "positive_factors"
            ]
        ):

            print(
                f"- {factor}"
            )

    else:

        print(
            "No major positive factors identified."
        )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "DONE"
    )

    print(
        "=" * 60
    )