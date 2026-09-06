"""
DPR Quality Assessor

Evaluates the quality of extracted DPR sections.

The assessment focuses on measurable document characteristics:

1. Content Length
2. Content Density
3. Numerical Evidence
4. Structural Quality
5. OCR / Text Quality
6. Section Coverage Quality

This module does NOT use an LLM.

The output will later be combined with:

- Completeness Assessment
- Quality Assessment
- Feature Construction
- ML Risk Scoring
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any


class QualityAssessor:

    def __init__(self):

        print("Quality Assessor initialized.")

        # Minimum characters expected for a meaningful section
        self.minimum_section_length = 300

        # Strong section length
        self.good_section_length = 1000

        # Maximum suspicious character ratio
        self.max_noise_ratio = 0.15


    # ============================================================
    # LOAD DOCUMENT
    # ============================================================

    def load_document(
        self,
        document_path: str
    ) -> Dict[str, Any]:

        print("\nLoading processed DPR...")

        path = Path(document_path)

        if not path.exists():

            raise FileNotFoundError(
                f"Document not found: {document_path}"
            )

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            document = json.load(file)

        print("Document loaded successfully.")

        return document


    # ============================================================
    # GET SECTIONS
    # ============================================================

    def get_sections(
        self,
        document: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        sections = document.get(
            "sections",
            []
        )

        if not isinstance(sections, list):

            print(
                "Warning: sections is not a list."
            )

            return []

        return sections


    # ============================================================
    # CONTENT LENGTH SCORE
    # ============================================================

    def assess_content_length(
        self,
        content: str
    ) -> Dict[str, Any]:

        length = len(content)

        if length == 0:

            score = 0.0
            level = "EMPTY"

        elif length < self.minimum_section_length:

            score = 0.4
            level = "VERY_SHORT"

        elif length < self.good_section_length:

            score = 0.7
            level = "ADEQUATE"

        else:

            score = 1.0
            level = "GOOD"

        return {

            "character_count": length,

            "score": round(
                score,
                3
            ),

            "level": level
        }


    # ============================================================
    # CONTENT DENSITY
    # ============================================================

    def assess_content_density(
        self,
        content: str
    ) -> Dict[str, Any]:

        if not content:

            return {

                "word_count": 0,

                "unique_word_count": 0,

                "density": 0.0,

                "score": 0.0
            }


        words = re.findall(

            r"\b[a-zA-Z]{2,}\b",

            content.lower()
        )


        word_count = len(words)


        if word_count == 0:

            return {

                "word_count": 0,

                "unique_word_count": 0,

                "density": 0.0,

                "score": 0.0
            }


        unique_words = len(
            set(words)
        )


        density = (
            unique_words /
            word_count
        )


        # Very low density may indicate:
        #
        # - repeated OCR text
        # - tables
        # - noisy extraction
        #
        # Normal prose generally has
        # reasonable vocabulary diversity.


        if density >= 0.45:

            score = 1.0

        elif density >= 0.30:

            score = 0.8

        elif density >= 0.20:

            score = 0.6

        else:

            score = 0.4


        return {

            "word_count": word_count,

            "unique_word_count":
                unique_words,

            "density":
                round(density, 3),

            "score":
                round(score, 3)
        }


    # ============================================================
    # NUMERICAL EVIDENCE
    # ============================================================

    def assess_numerical_evidence(
        self,
        content: str
    ) -> Dict[str, Any]:

        if not content:

            return {

                "numbers_found": 0,

                "score": 0.0
            }


        # Detect:
        #
        # 100
        # 100.5
        # 18,000
        # 12%
        # 4-lane
        #
        numbers = re.findall(

            r"\b\d+(?:,\d{3})*(?:\.\d+)?%?\b",

            content
        )


        number_count = len(
            numbers
        )


        if number_count >= 10:

            score = 1.0

        elif number_count >= 5:

            score = 0.8

        elif number_count >= 2:

            score = 0.6

        elif number_count >= 1:

            score = 0.4

        else:

            score = 0.2


        return {

            "numbers_found":
                number_count,

            "score":
                round(score, 3)
        }


    # ============================================================
    # STRUCTURAL QUALITY
    # ============================================================

    def assess_structure(
        self,
        content: str
    ) -> Dict[str, Any]:

        if not content:

            return {

                "paragraph_count": 0,

                "heading_candidates": 0,

                "score": 0.0
            }


        lines = [

            line.strip()

            for line in content.splitlines()

            if line.strip()
        ]


        paragraph_count = len(lines)


        heading_candidates = 0


        for line in lines:

            # Possible headings:
            #
            # ROAD ALIGNMENT
            # 5.2 DESIGN STANDARDS
            # CHAPTER V
            #
            if (

                len(line) < 120

                and (
                    line.isupper()

                    or re.match(
                        r"^\d+(\.\d+)*",
                        line
                    )
                )
            ):

                heading_candidates += 1


        if paragraph_count >= 5:

            paragraph_score = 1.0

        elif paragraph_count >= 3:

            paragraph_score = 0.7

        else:

            paragraph_score = 0.4


        if heading_candidates >= 1:

            heading_score = 1.0

        else:

            heading_score = 0.6


        final_score = (

            paragraph_score * 0.6

            +

            heading_score * 0.4
        )


        return {

            "paragraph_count":
                paragraph_count,

            "heading_candidates":
                heading_candidates,

            "score":
                round(
                    final_score,
                    3
                )
        }


    # ============================================================
    # TEXT / OCR QUALITY
    # ============================================================

    def assess_text_quality(
        self,
        content: str
    ) -> Dict[str, Any]:

        if not content:

            return {

                "noise_ratio": 1.0,

                "suspicious_characters": 0,

                "score": 0.0
            }


        total_characters = len(
            content
        )


        # Suspicious OCR characters.
        #
        # These often appear when OCR fails
        # or when encoding is corrupted.
        #
        suspicious_patterns = [

            "â€",

            "Ã",

            "�",

            "¤",

            "�"
        ]


        suspicious_count = 0


        for pattern in suspicious_patterns:

            suspicious_count += (

                content.count(pattern)
                *
                len(pattern)
            )


        # Also check unusual characters.

        unusual_characters = len(

            re.findall(

                r"[^\w\s.,;:!?()\[\]{}'\"/%&+\-=]",
                
                content
            )
        )


        suspicious_count += (
            unusual_characters
        )


        noise_ratio = (

            suspicious_count
            /
            max(
                total_characters,
                1
            )
        )


        if noise_ratio <= 0.01:

            score = 1.0

        elif noise_ratio <= 0.03:

            score = 0.8

        elif noise_ratio <= 0.07:

            score = 0.6

        elif noise_ratio <= self.max_noise_ratio:

            score = 0.4

        else:

            score = 0.2


        return {

            "noise_ratio":
                round(
                    noise_ratio,
                    4
                ),

            "suspicious_characters":
                suspicious_count,

            "score":
                round(
                    score,
                    3
                )
        }


    # ============================================================
    # ASSESS SINGLE SECTION
    # ============================================================

    def assess_section(
        self,
        section: Dict[str, Any]
    ) -> Dict[str, Any]:

        section_id = section.get(
            "section_id",
            "UNKNOWN"
        )


        title = section.get(
            "title",
            "Unknown Section"
        )


        content = section.get(
            "content",
            ""
        )


        print(

            f"\nAssessing section: "
            f"{section_id} | {title}"
        )


        length_result = (

            self.assess_content_length(
                content
            )
        )


        density_result = (

            self.assess_content_density(
                content
            )
        )


        numerical_result = (

            self.assess_numerical_evidence(
                content
            )
        )


        structure_result = (

            self.assess_structure(
                content
            )
        )


        text_result = (

            self.assess_text_quality(
                content
            )
        )


        # ========================================================
        # FINAL SECTION QUALITY SCORE
        # ========================================================

        quality_score = (

            length_result["score"]
            * 0.25

            +

            density_result["score"]
            * 0.20

            +

            numerical_result["score"]
            * 0.15

            +

            structure_result["score"]
            * 0.20

            +

            text_result["score"]
            * 0.20
        )


        quality_score = round(
            quality_score,
            3
        )


        # ========================================================
        # QUALITY LEVEL
        # ========================================================

        if quality_score >= 0.85:

            quality_level = "EXCELLENT"

        elif quality_score >= 0.70:

            quality_level = "GOOD"

        elif quality_score >= 0.50:

            quality_level = "MODERATE"

        else:

            quality_level = "POOR"


        print(

            f"QUALITY | "
            f"{section_id} | "
            f"Score: {quality_score} | "
            f"{quality_level}"
        )


        return {

            "section_id":
                section_id,

            "title":
                title,

            "quality_score":
                quality_score,

            "quality_percentage":
                round(
                    quality_score * 100,
                    2
                ),

            "quality_level":
                quality_level,


            "metrics": {

                "content_length":
                    length_result,

                "content_density":
                    density_result,

                "numerical_evidence":
                    numerical_result,

                "structural_quality":
                    structure_result,

                "text_quality":
                    text_result
            }
        }


    # ============================================================
    # ASSESS ENTIRE DOCUMENT
    # ============================================================

    def assess_document(
        self,
        document: Dict[str, Any]
    ) -> Dict[str, Any]:

        print(
            "\nAssessing document quality..."
        )


        metadata = document.get(
            "metadata",
            {}
        )


        filename = metadata.get(
            "filename",
            "unknown_document"
        )


        sections = self.get_sections(
            document
        )


        print(
            f"Document: {filename}"
        )


        print(
            f"Sections: {len(sections)}"
        )


        if not sections:

            return {

                "metadata": {

                    "filename":
                        filename
                },

                "document_quality_score":
                    0.0,

                "document_quality_percentage":
                    0.0,

                "document_quality_level":
                    "UNKNOWN",

                "sections":
                    []
            }


        section_results = []


        for section in sections:

            result = self.assess_section(
                section
            )

            section_results.append(
                result
            )


        # ========================================================
        # DOCUMENT QUALITY
        # ========================================================

        scores = [

            section["quality_score"]

            for section
            in section_results
        ]


        average_score = (

            sum(scores)
            /
            len(scores)
        )


        average_score = round(
            average_score,
            3
        )


        # ========================================================
        # WEIGHTED QUALITY
        #
        # Larger sections contain more document information.
        #
        # Therefore we calculate a weighted score based
        # on section content size.
        # ========================================================

        total_characters = 0

        weighted_sum = 0


        for section_result, section in zip(

            section_results,
            sections
        ):


            content = section.get(
                "content",
                ""
            )


            length = len(content)


            total_characters += length


            weighted_sum += (

                section_result["quality_score"]
                *
                length
            )


        if total_characters > 0:

            weighted_score = (

                weighted_sum
                /
                total_characters
            )

        else:

            weighted_score = 0.0


        weighted_score = round(
            weighted_score,
            3
        )


        # ========================================================
        # DOCUMENT QUALITY LEVEL
        # ========================================================

        if weighted_score >= 0.85:

            document_level = "EXCELLENT"

        elif weighted_score >= 0.70:

            document_level = "GOOD"

        elif weighted_score >= 0.50:

            document_level = "MODERATE"

        else:

            document_level = "POOR"


        # ========================================================
        # IDENTIFY WEAK SECTIONS
        # ========================================================

        weak_sections = [

            section

            for section
            in section_results

            if section["quality_score"]
            < 0.60
        ]


        excellent_sections = [

            section

            for section
            in section_results

            if section["quality_score"]
            >= 0.85
        ]


        return {

            "metadata": {

                "filename":
                    filename,

                "total_sections":
                    len(sections)
            },


            "document_quality_score":
                weighted_score,


            "document_quality_percentage":

                round(
                    weighted_score * 100,
                    2
                ),


            "average_section_quality":

                average_score,


            "document_quality_level":

                document_level,


            "weak_sections": [

                {

                    "section_id":
                        section["section_id"],

                    "title":
                        section["title"],

                    "quality_score":
                        section["quality_score"]

                }

                for section
                in weak_sections
            ],


            "excellent_sections": [

                {

                    "section_id":
                        section["section_id"],

                    "title":
                        section["title"],

                    "quality_score":
                        section["quality_score"]

                }

                for section
                in excellent_sections
            ],


            "sections":

                section_results
        }


    # ============================================================
    # SAVE RESULT
    # ============================================================

    def save_assessment(
        self,
        assessment: Dict[str, Any],
        output_path: str
    ) -> None:

        path = Path(
            output_path
        )


        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )


        with open(

            path,

            "w",

            encoding="utf-8"

        ) as file:


            json.dump(

                assessment,

                file,

                indent=4,

                ensure_ascii=False
            )


        print(
            "\nAssessment saved successfully:"
        )

        print(
            output_path
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "\n"
        + "=" * 60
    )


    print(
        "STARTING DPR QUALITY ASSESSMENT"
    )


    print(
        "=" * 60
    )


    INPUT_PATH = (

        "data/processed/"
        "DPR of Road.json"
    )


    OUTPUT_PATH = (

        "data/processed/"
        "DPR of Road_quality.json"
    )


    assessor = QualityAssessor()


    document = (

        assessor.load_document(
            INPUT_PATH
        )
    )


    assessment = (

        assessor.assess_document(
            document
        )
    )


    print(
        "\n"
        + "=" * 60
    )


    print(
        "QUALITY ASSESSMENT COMPLETE"
    )


    print(
        "=" * 60
    )


    print(

        f"\nDocument Quality: "

        f"{assessment['document_quality_percentage']}%"
    )


    print(

        f"Average Section Quality: "

        f"{round(assessment['average_section_quality'] * 100, 2)}%"
    )


    print(

        f"Quality Level: "

        f"{assessment['document_quality_level']}"
    )


    print(

        f"\nWeak Sections: "

        f"{len(assessment['weak_sections'])}"
    )


    if assessment["weak_sections"]:

        print(
            "\nWEAK SECTIONS:"
        )


        for section in assessment[
            "weak_sections"
        ]:


            print(

                f"\n- "
                f"{section['section_id']} | "
                f"{section['title']}"
            )


            print(

                f"  Quality Score: "

                f"{section['quality_score']}"
            )


    assessor.save_assessment(

        assessment,

        OUTPUT_PATH
    )


    print(
        "\n"
        + "=" * 60
    )


    print(
        "FINAL RESULT"
    )


    print(
        "=" * 60
    )


    print(

        f"\nDocument: "

        f"{assessment['metadata']['filename']}"
    )


    print(

        f"Total Sections: "

        f"{assessment['metadata']['total_sections']}"
    )


    print(

        f"Document Quality: "

        f"{assessment['document_quality_percentage']}%"
    )


    print(

        f"Quality Level: "

        f"{assessment['document_quality_level']}"
    )


    print(

        f"Weak Sections: "

        f"{len(assessment['weak_sections'])}"
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