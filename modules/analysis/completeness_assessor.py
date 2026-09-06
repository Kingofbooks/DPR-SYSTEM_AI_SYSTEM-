import json
import re
from pathlib import Path
from typing import Any


class CompletenessAssessor:
    """
    Assesses whether a DPR contains the expected sections.

    Current implementation supports template-based assessment.
    The design allows adding templates for different DPR types
    in the future.
    """

    def __init__(self) -> None:
        print("Completeness Assessor initialized.")

        self.templates = {
            "road_dpr": self._get_road_dpr_template()
        }

    # ============================================================
    # DPR TEMPLATES
    # ============================================================

    def _get_road_dpr_template(self) -> list[dict[str, Any]]:
        """
        Expected structure for a Road DPR.

        Each item contains:
        - id
        - name
        - keywords
        - critical
        """

        return [

            {
                "id": "project_overview",
                "name": "Project Overview",
                "keywords": [
                    "project overview",
                    "introduction",
                    "project description",
                    "project background",
                    "executive summary"
                ],
                "critical": True
            },

            {
                "id": "project_location",
                "name": "Project Location",
                "keywords": [
                    "project location",
                    "location",
                    "project area",
                    "location of project"
                ],
                "critical": True
            },

            {
                "id": "existing_conditions",
                "name": "Existing Conditions",
                "keywords": [
                    "existing condition",
                    "existing road",
                    "existing alignment",
                    "road inventory",
                    "existing scenario"
                ],
                "critical": True
            },

            {
                "id": "traffic_analysis",
                "name": "Traffic Analysis",
                "keywords": [
                    "traffic analysis",
                    "traffic survey",
                    "traffic study",
                    "traffic volume",
                    "traffic forecast",
                    "traffic projection"
                ],
                "critical": True
            },

            {
                "id": "alignment",
                "name": "Road Alignment",
                "keywords": [
                    "alignment",
                    "proposed alignment",
                    "horizontal alignment",
                    "vertical alignment",
                    "alignment of proposed road"
                ],
                "critical": True
            },

            {
                "id": "design_standards",
                "name": "Design Standards",
                "keywords": [
                    "design standards",
                    "design standard",
                    "geometric design",
                    "irc standards",
                    "design criteria"
                ],
                "critical": True
            },

            {
                "id": "cross_section",
                "name": "Cross Sectional Elements",
                "keywords": [
                    "cross sectional",
                    "cross section",
                    "cross-sectional elements",
                    "typical cross section"
                ],
                "critical": False
            },

            {
                "id": "pavement_design",
                "name": "Pavement Design",
                "keywords": [
                    "pavement design",
                    "pavement",
                    "flexible pavement",
                    "rigid pavement",
                    "pavement composition"
                ],
                "critical": True
            },

            {
                "id": "bridges_structures",
                "name": "Bridges and Structures",
                "keywords": [
                    "bridges",
                    "bridge",
                    "culverts",
                    "cross drainage",
                    "road structures"
                ],
                "critical": True
            },

            {
                "id": "environmental_impact",
                "name": "Environmental Impact",
                "keywords": [
                    "environmental impact",
                    "environment",
                    "eia",
                    "environmental assessment",
                    "environmental clearance"
                ],
                "critical": True
            },

            {
                "id": "land_acquisition",
                "name": "Land Acquisition",
                "keywords": [
                    "land acquisition",
                    "land requirement",
                    "right of way",
                    "row"
                ],
                "critical": True
            },

            {
                "id": "economic_analysis",
                "name": "Economic Analysis",
                "keywords": [
                    "economic analysis",
                    "economic evaluation",
                    "economic viability",
                    "economic benefits",
                    "cost benefit"
                ],
                "critical": True
            },

            {
                "id": "cost_estimate",
                "name": "Cost Estimate",
                "keywords": [
                    "cost estimate",
                    "project cost",
                    "estimated cost",
                    "cost estimation",
                    "project cost estimate"
                ],
                "critical": True
            },

            {
                "id": "implementation_schedule",
                "name": "Implementation Schedule",
                "keywords": [
                    "implementation schedule",
                    "construction schedule",
                    "project schedule",
                    "implementation plan",
                    "work programme"
                ],
                "critical": False
            },

            {
                "id": "road_safety",
                "name": "Road Safety",
                "keywords": [
                    "road safety",
                    "traffic signs",
                    "road markings",
                    "road furniture",
                    "safety measures"
                ],
                "critical": False
            },

            {
                "id": "consultancy",
                "name": "Consultancy",
                "keywords": [
                    "consultancy",
                    "consultant",
                    "consulting services"
                ],
                "critical": False
            }
        ]

    # ============================================================
    # TEXT NORMALIZATION
    # ============================================================

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for matching.
        """

        if not isinstance(text, str):
            return ""

        text = text.lower()

        text = text.replace("-", " ")
        text = text.replace("_", " ")

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # ============================================================
    # GET DOCUMENT SECTIONS
    # ============================================================

    def _get_document_sections(
        self,
        document_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Extract sections from processed DPR JSON.

        Supports the current pipeline structure:

        {
            "metadata": {...},
            "toc": {...},
            "parsed_sections": [...],
            "mapped_sections": [...],
            "sections": [...]
        }
        """

        sections = document_data.get("sections", [])

        if not isinstance(sections, list):
            sections = []

        return sections

    # ============================================================
    # BUILD SEARCHABLE DOCUMENT TEXT
    # ============================================================

    def _build_document_text(
        self,
        sections: list[dict[str, Any]]
    ) -> str:
        """
        Builds a searchable representation of all sections.

        We use:
        - Section ID
        - Title
        - Content

        Content is included because sometimes the parser
        may produce imperfect OCR titles.
        """

        parts = []

        for section in sections:

            if not isinstance(section, dict):
                continue

            section_id = str(
                section.get("section_id", "")
            )

            title = str(
                section.get("title", "")
            )

            content = str(
                section.get("content", "")
            )

            section_text = (
                f"{section_id} "
                f"{title} "
                f"{content}"
            )

            parts.append(section_text)

        return self._normalize_text(
            " ".join(parts)
        )

    # ============================================================
    # MATCH A TEMPLATE SECTION
    # ============================================================

    def _find_matching_sections(
        self,
        expected_section: dict[str, Any],
        document_sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Find document sections matching an expected section.

        Matching priority:

        1. Exact keyword match in title
        2. Keyword phrase contained in title
        3. Keyword phrase found in content
        """

        keywords = expected_section.get(
            "keywords",
            []
        )

        matches = []

        for section in document_sections:

            if not isinstance(section, dict):
                continue

            section_id = str(
                section.get("section_id", "")
            )

            title = str(
                section.get("title", "")
            )

            content = str(
                section.get("content", "")
            )

            normalized_title = self._normalize_text(title)

            normalized_content = self._normalize_text(
                content
            )

            best_score = 0.0
            matched_keyword = None

            for keyword in keywords:

                normalized_keyword = (
                    self._normalize_text(keyword)
                )

                if not normalized_keyword:
                    continue

                # --------------------------------------------
                # EXACT TITLE MATCH
                # --------------------------------------------

                if (
                    normalized_title
                    == normalized_keyword
                ):

                    score = 1.0

                # --------------------------------------------
                # KEYWORD INSIDE TITLE
                # --------------------------------------------

                elif (
                    normalized_keyword
                    in normalized_title
                ):

                    score = 0.95

                # --------------------------------------------
                # TITLE WORD OVERLAP
                # --------------------------------------------

                else:

                    keyword_words = set(
                        normalized_keyword.split()
                    )

                    title_words = set(
                        normalized_title.split()
                    )

                    if keyword_words:

                        overlap = (
                            len(
                                keyword_words
                                & title_words
                            )
                            / len(keyword_words)
                        )

                    else:

                        overlap = 0.0

                    if overlap >= 0.75:

                        score = (
                            0.60
                            + overlap * 0.25
                        )

                    elif (
                        normalized_keyword
                        in normalized_content
                    ):

                        score = 0.70

                    else:

                        score = 0.0

                if score > best_score:

                    best_score = score

                    matched_keyword = keyword

            if best_score > 0:

                matches.append({

                    "section_id": section_id,

                    "title": title,

                    "score": round(
                        best_score,
                        3
                    ),

                    "matched_keyword":
                        matched_keyword

                })

        matches.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return matches

    # ============================================================
    # ASSESS COMPLETENESS
    # ============================================================

    def assess(
        self,
        document_data: dict[str, Any],
        template_name: str = "road_dpr"
    ) -> dict[str, Any]:
        """
        Assess DPR completeness.

        Parameters
        ----------
        document_data:
            Processed DPR JSON data.

        template_name:
            DPR template to use.

        Returns
        -------
        dict
            Completeness assessment result.
        """

        print("\nAssessing document completeness...")

        # --------------------------------------------------------
        # VALIDATE TEMPLATE
        # --------------------------------------------------------

        if template_name not in self.templates:

            raise ValueError(
                f"Unknown template: "
                f"{template_name}"
            )

        template = self.templates[
            template_name
        ]

        # --------------------------------------------------------
        # GET DOCUMENT SECTIONS
        # --------------------------------------------------------

        document_sections = (
            self._get_document_sections(
                document_data
            )
        )

        metadata = document_data.get(
            "metadata",
            {}
        )

        filename = metadata.get(
            "filename",
            "unknown_document"
        )

        print(f"Document: {filename}")

        print(
            f"Document Sections: "
            f"{len(document_sections)}"
        )

        print(
            f"Expected Sections: "
            f"{len(template)}"
        )

        # --------------------------------------------------------
        # ASSESS EACH EXPECTED SECTION
        # --------------------------------------------------------

        found_sections = []

        missing_sections = []

        critical_missing_sections = []

        assessment_details = []

        for expected_section in template:

            expected_id = expected_section[
                "id"
            ]

            expected_name = expected_section[
                "name"
            ]

            is_critical = expected_section[
                "critical"
            ]

            matches = (
                self._find_matching_sections(
                    expected_section,
                    document_sections
                )
            )

            # ----------------------------------------------------
            # FOUND
            # ----------------------------------------------------

            if matches:

                best_match = matches[0]

                result = {

                    "id": expected_id,

                    "name": expected_name,

                    "critical": is_critical,

                    "status": "FOUND",

                    "matched_section_id":
                        best_match["section_id"],

                    "matched_section_title":
                        best_match["title"],

                    "matched_keyword":
                        best_match[
                            "matched_keyword"
                        ],

                    "match_confidence":
                        best_match["score"]

                }

                found_sections.append(
                    result
                )

                print(

                    f"FOUND   | "
                    f"{expected_name} | "
                    f"Matched: "
                    f"{best_match['title']} | "
                    f"Confidence: "
                    f"{best_match['score']}"

                )

            # ----------------------------------------------------
            # MISSING
            # ----------------------------------------------------

            else:

                result = {

                    "id": expected_id,

                    "name": expected_name,

                    "critical": is_critical,

                    "status": "MISSING",

                    "matched_section_id": None,

                    "matched_section_title": None,

                    "matched_keyword": None,

                    "match_confidence": 0.0

                }

                missing_sections.append(
                    result
                )

                if is_critical:

                    critical_missing_sections.append(
                        result
                    )

                print(

                    f"MISSING | "
                    f"{expected_name} | "
                    f"Critical: "
                    f"{is_critical}"

                )

            assessment_details.append(
                result
            )

        # --------------------------------------------------------
        # CALCULATE SCORES
        # --------------------------------------------------------

        total_expected = len(template)

        total_found = len(found_sections)

        total_missing = len(missing_sections)

        completeness_score = (
            total_found
            / total_expected
            if total_expected > 0
            else 0.0
        )

        # --------------------------------------------------------
        # CRITICAL SCORE
        # --------------------------------------------------------

        critical_sections = [

            section

            for section in template

            if section["critical"]

        ]

        total_critical = len(
            critical_sections
        )

        critical_found = len([

            section

            for section in found_sections

            if section["critical"]

        ])

        critical_completeness_score = (

            critical_found
            / total_critical

            if total_critical > 0

            else 0.0

        )

        # --------------------------------------------------------
        # WEIGHTED SCORE
        #
        # Critical sections matter more.
        #
        # 70% Critical Completeness
        # 30% Overall Completeness
        # --------------------------------------------------------

        weighted_score = (

            0.70
            * critical_completeness_score

            +

            0.30
            * completeness_score

        )

        # --------------------------------------------------------
        # DETERMINE LEVEL
        # --------------------------------------------------------

        if weighted_score >= 0.90:

            completeness_level = "EXCELLENT"

        elif weighted_score >= 0.75:

            completeness_level = "GOOD"

        elif weighted_score >= 0.50:

            completeness_level = "MODERATE"

        else:

            completeness_level = "POOR"

        # --------------------------------------------------------
        # BUILD RESULT
        # --------------------------------------------------------

        result = {

            "metadata": {

                "filename": filename,

                "template": template_name,

                "document_section_count":
                    len(document_sections),

                "expected_section_count":
                    total_expected

            },

            "summary": {

                "total_expected_sections":
                    total_expected,

                "found_sections":
                    total_found,

                "missing_sections":
                    total_missing,

                "critical_sections":
                    total_critical,

                "critical_sections_found":
                    critical_found,

                "critical_sections_missing":
                    len(
                        critical_missing_sections
                    )

            },

            "scores": {

                "completeness_score":
                    round(
                        completeness_score,
                        4
                    ),

                "completeness_percentage":
                    round(
                        completeness_score * 100,
                        2
                    ),

                "critical_completeness_score":
                    round(
                        critical_completeness_score,
                        4
                    ),

                "critical_completeness_percentage":
                    round(
                        critical_completeness_score
                        * 100,
                        2
                    ),

                "weighted_completeness_score":
                    round(
                        weighted_score,
                        4
                    ),

                "weighted_completeness_percentage":
                    round(
                        weighted_score
                        * 100,
                        2
                    )

            },

            "completeness_level":
                completeness_level,

            "found_sections":
                found_sections,

            "missing_sections":
                missing_sections,

            "critical_missing_sections":
                critical_missing_sections,

            "assessment_details":
                assessment_details

        }

        print("\n" + "=" * 60)

        print(
            "COMPLETENESS ASSESSMENT COMPLETE"
        )

        print("=" * 60)

        print(
            f"Completeness Score: "
            f"{result['scores']['completeness_percentage']}%"
        )

        print(
            f"Critical Completeness: "
            f"{result['scores']['critical_completeness_percentage']}%"
        )

        print(
            f"Weighted Score: "
            f"{result['scores']['weighted_completeness_percentage']}%"
        )

        print(
            f"Completeness Level: "
            f"{completeness_level}"
        )

        return result

    # ============================================================
    # LOAD DOCUMENT
    # ============================================================

    def load_document(
        self,
        file_path: str | Path
    ) -> dict[str, Any]:
        """
        Load processed DPR JSON.
        """

        file_path = Path(file_path)

        if not file_path.exists():

            raise FileNotFoundError(

                f"Document file not found:\n"
                f"{file_path}"

            )

        with open(

            file_path,

            "r",

            encoding="utf-8"

        ) as file:

            document_data = json.load(file)

        return document_data

    # ============================================================
    # SAVE ASSESSMENT
    # ============================================================

    def save_assessment(
        self,
        assessment_result: dict[str, Any],
        output_path: str | Path
    ) -> None:
        """
        Save completeness assessment.
        """

        output_path = Path(output_path)

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

                assessment_result,

                file,

                indent=4,

                ensure_ascii=False

            )

        print(

            "\nAssessment saved successfully:"

        )

        print(output_path)


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)

    print(
        "STARTING DPR COMPLETENESS ASSESSMENT"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # PATHS
    # --------------------------------------------------------

    INPUT_PATH = Path(
        "data/processed/DPR of Road.json"
    )

    OUTPUT_PATH = Path(
        "data/processed/"
        "DPR of Road_completeness.json"
    )

    # --------------------------------------------------------
    # INITIALIZE
    # --------------------------------------------------------

    assessor = CompletenessAssessor()

    # --------------------------------------------------------
    # LOAD DOCUMENT
    # --------------------------------------------------------

    print("\nLoading processed DPR...")

    document = assessor.load_document(
        INPUT_PATH
    )

    print(
        "Document loaded successfully."
    )

    # --------------------------------------------------------
    # ASSESS
    # --------------------------------------------------------

    result = assessor.assess(

        document_data=document,

        template_name="road_dpr"

    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    assessor.save_assessment(

        assessment_result=result,

        output_path=OUTPUT_PATH

    )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("FINAL COMPLETENESS RESULT")

    print("=" * 60)

    print()

    print(

        f"Document: "
        f"{result['metadata']['filename']}"

    )

    print(

        f"Expected Sections: "
        f"{result['summary']['total_expected_sections']}"

    )

    print(

        f"Found Sections: "
        f"{result['summary']['found_sections']}"

    )

    print(

        f"Missing Sections: "
        f"{result['summary']['missing_sections']}"

    )

    print(

        f"Critical Missing Sections: "
        f"{result['summary']['critical_sections_missing']}"

    )

    print()

    print(

        f"Completeness: "
        f"{result['scores']['completeness_percentage']}%"

    )

    print(

        f"Critical Completeness: "
        f"{result['scores']['critical_completeness_percentage']}%"

    )

    print(

        f"Weighted Completeness: "
        f"{result['scores']['weighted_completeness_percentage']}%"

    )

    print()

    print(

        f"LEVEL: "
        f"{result['completeness_level']}"

    )

    # --------------------------------------------------------
    # CRITICAL MISSING
    # --------------------------------------------------------

    if result[
        "critical_missing_sections"
    ]:

        print()

        print(
            "CRITICAL MISSING SECTIONS:"
        )

        print()

        for section in result[
            "critical_missing_sections"
        ]:

            print(
                f"- {section['name']}"
            )

    print("\n" + "=" * 60)

    print("DONE")

    print("=" * 60)