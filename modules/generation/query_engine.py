"""
Query Engine
============

Main interface for asking questions about a processed DPR document.

Pipeline:

User Question
      ↓
Query Engine
      ↓
RAG Generator
      ↓
Retriever
      ↓
Document Embeddings
      ↓
Gemini LLM
      ↓
Final Answer
"""

from pathlib import Path
import sys


# ============================================================
# PROJECT ROOT SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS
# ============================================================

from modules.generation.rag_generator import RAGGenerator


# ============================================================
# QUERY ENGINE
# ============================================================

class QueryEngine:
    """
    Main interface for querying a DPR document.

    This class acts as a simple wrapper around the RAG pipeline.
    """

    def __init__(self):
        """
        Initialize the query engine.
        """

        print("\n" + "=" * 60)
        print("QUERY ENGINE INITIALIZED")
        print("=" * 60)

        self.rag_generator = RAGGenerator()


    # ========================================================
    # ASK QUESTION
    # ========================================================

    def ask(
        self,
        question: str,
        top_k: int = 5
    ) -> dict:
        """
        Ask a question about the DPR document.

        Parameters
        ----------
        question : str
            User's question.

        top_k : int
            Number of relevant document chunks to retrieve.

        Returns
        -------
        dict
            Contains:
                - question
                - answer
                - sources
                - retrieved_chunks
        """

        # ----------------------------------------------------
        # VALIDATE QUESTION
        # ----------------------------------------------------

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        question = question.strip()

        if len(question) == 0:
            raise ValueError(
                "Question cannot be empty."
            )


        # ----------------------------------------------------
        # DISPLAY QUESTION
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print("PROCESSING QUERY")
        print("=" * 60)

        print("\nQuestion:")
        print(question)


        # ----------------------------------------------------
        # RUN RAG PIPELINE
        # ----------------------------------------------------

        try:

            result = self.rag_generator.generate(
                question=question,
                top_k=top_k
            )

        except Exception as error:

            print("\nERROR DURING QUERY PROCESSING")

            raise RuntimeError(
                f"Failed to process query: {error}"
            )


        # ----------------------------------------------------
        # RETURN RESULT
        # ----------------------------------------------------

        return result


    # ========================================================
    # INTERACTIVE MODE
    # ========================================================

    def start_interactive_mode(
        self,
        top_k: int = 5
    ):
        """
        Start an interactive terminal chat session.

        The user can continuously ask questions about the DPR.
        """

        print("\n" + "=" * 60)
        print("DPR AI QUERY SYSTEM")
        print("=" * 60)

        print("\nAsk questions about the DPR document.")

        print(
            "\nCommands:"
        )

        print(
            "  exit  - Exit the program"
        )

        print(
            "  quit  - Exit the program"
        )

        print(
            "  help  - Show available commands"
        )


        # ----------------------------------------------------
        # INTERACTIVE LOOP
        # ----------------------------------------------------

        while True:

            print("\n" + "-" * 60)

            try:

                question = input(
                    "\nYou: "
                )

            except KeyboardInterrupt:

                print(
                    "\n\nExiting DPR AI System..."
                )

                break


            # ------------------------------------------------
            # CLEAN INPUT
            # ------------------------------------------------

            question = question.strip()


            # ------------------------------------------------
            # EMPTY INPUT
            # ------------------------------------------------

            if not question:

                print(
                    "\nPlease enter a question."
                )

                continue


            # ------------------------------------------------
            # EXIT COMMANDS
            # ------------------------------------------------

            if question.lower() in [
                "exit",
                "quit",
                "q"
            ]:

                print(
                    "\nExiting DPR AI System..."
                )

                break


            # ------------------------------------------------
            # HELP COMMAND
            # ------------------------------------------------

            if question.lower() == "help":

                print(
                    "\nAvailable commands:"
                )

                print(
                    "  exit  - Exit the program"
                )

                print(
                    "  quit  - Exit the program"
                )

                print(
                    "  help  - Show this message"
                )

                continue


            # ------------------------------------------------
            # PROCESS QUESTION
            # ------------------------------------------------

            try:

                result = self.ask(
                    question=question,
                    top_k=top_k
                )


                # --------------------------------------------
                # DISPLAY ANSWER
                # --------------------------------------------

                print("\n" + "=" * 60)
                print("ANSWER")
                print("=" * 60)

                answer = result.get(
                    "answer",
                    "No answer generated."
                )

                print()
                print(answer)


                # --------------------------------------------
                # DISPLAY SOURCES
                # --------------------------------------------

                sources = result.get(
                    "sources",
                    []
                )


                if sources:

                    print("\n" + "=" * 60)
                    print("SOURCES")
                    print("=" * 60)


                    for index, source in enumerate(
                        sources,
                        start=1
                    ):

                        print(
                            f"\n{index}. "
                            f"Section: "
                            f"{source.get('section_id', 'Unknown')}"
                        )

                        print(
                            f"   Title: "
                            f"{source.get('section_title', 'Unknown')}"
                        )


                        similarity = source.get(
                            "similarity",
                            None
                        )


                        if similarity is not None:

                            try:

                                print(
                                    f"   Relevance: "
                                    f"{float(similarity):.4f}"
                                )

                            except (
                                ValueError,
                                TypeError
                            ):

                                print(
                                    f"   Relevance: "
                                    f"{similarity}"
                                )


            # ------------------------------------------------
            # HANDLE ERRORS
            # ------------------------------------------------

            except Exception as error:

                print(
                    "\nERROR:"
                )

                print(error)


        # ----------------------------------------------------
        # END
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print("QUERY SESSION ENDED")
        print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    engine = QueryEngine()

    engine.start_interactive_mode(
        top_k=5
    )