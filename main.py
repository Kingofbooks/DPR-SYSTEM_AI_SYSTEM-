"""
============================================================
DPR AI SYSTEM
MASTER PIPELINE
============================================================

This file acts as the central entry point for the DPR AI System.

Pipeline:

PDF
 ↓
Document Processing
 ↓
Completeness Assessment
 ↓
Quality Assessment
 ↓
Feature Construction
 ↓
Risk Scoring
 ↓
Chunking
 ↓
Embedding
 ↓
Ready for RAG Queries

============================================================
"""

import argparse
import subprocess
import sys
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


# ============================================================
# PIPELINE RUNNER
# ============================================================

class DPRPipeline:
    """
    Master controller for the DPR AI System.

    This class orchestrates all modules in the pipeline.
    """

    def __init__(
        self,
        pdf_path=None,
        run_retrieval=True,
        run_analysis=True,
    ):

        self.pdf_path = (
            Path(pdf_path).resolve()
            if pdf_path
            else None
        )

        self.run_retrieval = run_retrieval
        self.run_analysis = run_analysis

        print("\n")

        print("=" * 60)
        print("DPR AI SYSTEM")
        print("MASTER PIPELINE INITIALIZED")
        print("=" * 60)

        print(f"\nProject Root:")
        print(PROJECT_ROOT)

        print(f"\nRaw Data Directory:")
        print(RAW_DATA_DIR)

        print(f"\nProcessed Data Directory:")
        print(PROCESSED_DATA_DIR)

        if self.pdf_path:

            print(f"\nSelected PDF:")
            print(self.pdf_path)

        print("\n")


    # ========================================================
    # RUN MODULE
    # ========================================================

    def run_module(
        self,
        module_name,
        step_name,
    ):
        """
        Run a Python module.

        Example:

        modules.processing.document_processor
        """

        print("\n")

        print("=" * 60)

        print(f"RUNNING: {step_name}")

        print("=" * 60)

        print()

        command = [

            "uv",

            "run",

            "python",

            "-m",

            module_name,

        ]


        try:

            result = subprocess.run(

                command,

                cwd=PROJECT_ROOT,

                check=True,

            )


            print("\n")

            print("-" * 60)

            print(f"{step_name} COMPLETED SUCCESSFULLY")

            print("-" * 60)


            return True


        except subprocess.CalledProcessError:

            print("\n")

            print("=" * 60)

            print(f"ERROR IN: {step_name}")

            print("=" * 60)

            print()

            print(
                f"The pipeline stopped while running:\n"
                f"{module_name}"
            )


            return False


        except FileNotFoundError:

            print("\n")

            print("=" * 60)

            print("ERROR: UV COMMAND NOT FOUND")

            print("=" * 60)

            print()

            print(
                "Could not find the 'uv' command."
            )

            print(
                "Make sure uv is installed and available "
                "in your system PATH."
            )


            return False


    # ========================================================
    # CHECK PDF
    # ========================================================

    def validate_pdf(self):

        print("\n")

        print("=" * 60)

        print("VALIDATING INPUT")

        print("=" * 60)


        # ----------------------------------------------------
        # CASE 1
        #
        # PDF PATH PROVIDED
        # ----------------------------------------------------

        if self.pdf_path:

            if not self.pdf_path.exists():

                print("\nERROR: PDF FILE NOT FOUND")

                print(self.pdf_path)

                return False


            if self.pdf_path.suffix.lower() != ".pdf":

                print("\nERROR: INPUT FILE IS NOT A PDF")

                print(self.pdf_path)

                return False


            print("\nPDF FOUND")

            print(f"Filename: {self.pdf_path.name}")

            return True


        # ----------------------------------------------------
        # CASE 2
        #
        # NO PDF PATH PROVIDED
        # ----------------------------------------------------

        RAW_DATA_DIR.mkdir(

            parents=True,

            exist_ok=True,

        )


        pdf_files = list(

            RAW_DATA_DIR.glob("*.pdf")

        )


        if not pdf_files:

            print("\nNO PDF FILE FOUND")

            print("\nPlease either:")

            print(
                "\n1. Place a PDF inside:"
            )

            print(
                RAW_DATA_DIR
            )

            print(
                "\nOR"
            )

            print(
                "\n2. Provide a PDF path:"
            )

            print(
                "\nuv run python main.py "
                "--pdf path/to/document.pdf"
            )


            return False


        print("\nPDF FILES FOUND:")


        for index, pdf_file in enumerate(

            pdf_files,

            start=1,

        ):

            print(

                f"{index}. {pdf_file.name}"

            )


        return True


    # ========================================================
    # STEP 1
    # DOCUMENT PROCESSING
    # ========================================================

    def process_document(self):

        return self.run_module(

            module_name=(
                "modules.processing.document_processor"
            ),

            step_name=(
                "STEP 1: DOCUMENT PROCESSING"
            ),

        )


    # ========================================================
    # STEP 2
    # COMPLETENESS ASSESSMENT
    # ========================================================

    def assess_completeness(self):

        return self.run_module(

            module_name=(
                "modules.analysis.completeness_assessor"
            ),

            step_name=(
                "STEP 2: COMPLETENESS ASSESSMENT"
            ),

        )


    # ========================================================
    # STEP 3
    # QUALITY ASSESSMENT
    # ========================================================

    def assess_quality(self):

        return self.run_module(

            module_name=(
                "modules.analysis.quality_assessor"
            ),

            step_name=(
                "STEP 3: QUALITY ASSESSMENT"
            ),

        )


    # ========================================================
    # STEP 4
    # FEATURE CONSTRUCTION
    # ========================================================

    def construct_features(self):

        return self.run_module(

            module_name=(
                "modules.analysis.feature_constructor"
            ),

            step_name=(
                "STEP 4: FEATURE CONSTRUCTION"
            ),

        )


    # ========================================================
    # STEP 5
    # RISK SCORING
    # ========================================================

    def calculate_risk(self):

        return self.run_module(

            module_name=(
                "modules.analysis.risk_scorer"
            ),

            step_name=(
                "STEP 5: RISK SCORING"
            ),

        )


    # ========================================================
    # STEP 6
    # DOCUMENT CHUNKING
    # ========================================================

    def chunk_document(self):

        return self.run_module(

            module_name=(
                "modules.retrieval.chunker"
            ),

            step_name=(
                "STEP 6: DOCUMENT CHUNKING"
            ),

        )


    # ========================================================
    # STEP 7
    # DOCUMENT EMBEDDING
    # ========================================================

    def embed_document(self):

        return self.run_module(

            module_name=(
                "modules.retrieval.embedder"
            ),

            step_name=(
                "STEP 7: DOCUMENT EMBEDDING"
            ),

        )


    # ========================================================
    # RUN ANALYSIS PIPELINE
    # ========================================================

    def run_analysis_pipeline(self):

        print("\n")

        print("=" * 60)

        print("STARTING ANALYSIS PIPELINE")

        print("=" * 60)


        # ----------------------------------------------------
        # COMPLETENESS
        # ----------------------------------------------------

        success = self.assess_completeness()

        if not success:

            return False


        # ----------------------------------------------------
        # QUALITY
        # ----------------------------------------------------

        success = self.assess_quality()

        if not success:

            return False


        # ----------------------------------------------------
        # FEATURES
        # ----------------------------------------------------

        success = self.construct_features()

        if not success:

            return False


        # ----------------------------------------------------
        # RISK
        # ----------------------------------------------------

        success = self.calculate_risk()

        if not success:

            return False


        return True


    # ========================================================
    # RUN RETRIEVAL PIPELINE
    # ========================================================

    def run_retrieval_pipeline(self):

        print("\n")

        print("=" * 60)

        print("STARTING RETRIEVAL PIPELINE")

        print("=" * 60)


        # ----------------------------------------------------
        # CHUNKING
        # ----------------------------------------------------

        success = self.chunk_document()

        if not success:

            return False


        # ----------------------------------------------------
        # EMBEDDING
        # ----------------------------------------------------

        success = self.embed_document()

        if not success:

            return False


        return True


    # ========================================================
    # RUN COMPLETE PIPELINE
    # ========================================================

    def run(self):

        print("\n")

        print("=" * 60)

        print("STARTING DPR AI PIPELINE")

        print("=" * 60)


        # ----------------------------------------------------
        # VALIDATE INPUT
        # ----------------------------------------------------

        valid = self.validate_pdf()


        if not valid:

            return False


        # ----------------------------------------------------
        # CREATE DIRECTORIES
        # ----------------------------------------------------

        RAW_DATA_DIR.mkdir(

            parents=True,

            exist_ok=True,

        )


        PROCESSED_DATA_DIR.mkdir(

            parents=True,

            exist_ok=True,

        )


        # ----------------------------------------------------
        # STEP 1
        #
        # PROCESS DOCUMENT
        # ----------------------------------------------------

        success = self.process_document()


        if not success:

            print("\nPipeline stopped.")

            return False


        # ----------------------------------------------------
        # STEP 2
        #
        # ANALYSIS
        # ----------------------------------------------------

        if self.run_analysis:

            success = self.run_analysis_pipeline()


            if not success:

                print("\nAnalysis pipeline failed.")

                return False


        # ----------------------------------------------------
        # STEP 3
        #
        # RETRIEVAL
        # ----------------------------------------------------

        if self.run_retrieval:

            success = self.run_retrieval_pipeline()


            if not success:

                print("\nRetrieval pipeline failed.")

                return False


        # ----------------------------------------------------
        # COMPLETE
        # ----------------------------------------------------

        self.print_final_status()


        return True


    # ========================================================
    # FINAL STATUS
    # ========================================================

    def print_final_status(self):

        print("\n")

        print("=" * 60)

        print("DPR AI PIPELINE COMPLETED SUCCESSFULLY")

        print("=" * 60)


        print("\nGENERATED OUTPUTS")


        output_files = list(

            PROCESSED_DATA_DIR.glob("*")

        )


        if output_files:

            print()


            for file in output_files:

                print(

                    f"✓ {file.name}"

                )


        else:

            print(

                "\nNo processed files found."

            )


        print("\n")


        print("=" * 60)

        print("SYSTEM READY")

        print("=" * 60)


        print(

            "\nThe DPR has been processed and analyzed."
        )


        print(

            "\nAvailable capabilities:"
        )


        print(

            "\n1. Completeness Assessment"
        )

        print(

            "2. Quality Assessment"
        )

        print(

            "3. Feature Construction"
        )

        print(

            "4. Risk Assessment"
        )

        print(

            "5. Semantic Retrieval"
        )

        print(

            "6. RAG Question Answering"
        )


        print("\n")


# ============================================================
# ARGUMENT PARSER
# ============================================================

def parse_arguments():

    parser = argparse.ArgumentParser(

        description=(
            "DPR AI System - Master Pipeline"
        )

    )


    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    parser.add_argument(

        "--pdf",

        type=str,

        default=None,

        help=(
            "Path to the input PDF document"
        ),

    )


    # --------------------------------------------------------
    # SKIP RETRIEVAL
    # --------------------------------------------------------

    parser.add_argument(

        "--skip-retrieval",

        action="store_true",

        help=(
            "Skip chunking and embedding"
        ),

    )


    # --------------------------------------------------------
    # SKIP ANALYSIS
    # --------------------------------------------------------

    parser.add_argument(

        "--skip-analysis",

        action="store_true",

        help=(
            "Skip completeness, quality, "
            "feature construction and risk scoring"
        ),

    )


    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main():

    arguments = parse_arguments()


    pipeline = DPRPipeline(

        pdf_path=arguments.pdf,

        run_retrieval=(
            not arguments.skip_retrieval
        ),

        run_analysis=(
            not arguments.skip_analysis
        ),

    )


    success = pipeline.run()


    if success:

        print(

            "\nDPR AI SYSTEM FINISHED SUCCESSFULLY.\n"

        )

        sys.exit(0)


    else:

        print(

            "\nDPR AI SYSTEM FAILED.\n"

        )

        sys.exit(1)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()