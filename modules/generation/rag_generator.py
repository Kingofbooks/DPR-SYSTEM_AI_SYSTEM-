import os
from typing import List, Dict, Any

from dotenv import load_dotenv
from google import genai

from modules.retrieval.retriever import DocumentRetriever

load_dotenv()
# ==========================================================
# RAG GENERATOR
# ==========================================================

class RAGGenerator:
    """
    Complete RAG Pipeline.

    Pipeline:

    User Question
        ↓
    Retriever
        ↓
    Relevant Document Chunks
        ↓
    Context Builder
        ↓
    Prompt Builder
        ↓
    Gemini LLM
        ↓
    Grounded Answer
    """

    def __init__(
        self,
        top_k: int = 5,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        embeddings_path: str = "data/processed/DPR of Road_embeddings.json",
        model_name: str = "gemini-2.5-flash",
    ):
        """
        Initialize the RAG Generator.
        """

        print("RAG Generator initialized.")

        # --------------------------------------------------
        # LOAD ENVIRONMENT VARIABLES
        # --------------------------------------------------

        load_dotenv()

        self.api_key = os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found.\n"
                "Please add it to your .env file."
            )

        # --------------------------------------------------
        # CONFIGURATION
        # --------------------------------------------------

        self.top_k = top_k
        self.model_name = model_name

        # --------------------------------------------------
        # INITIALIZE RETRIEVER
        # --------------------------------------------------

        self.retriever = DocumentRetriever(
            embedding_model_name=embedding_model_name,
            embeddings_path=embeddings_path,
        )

        # --------------------------------------------------
        # INITIALIZE GEMINI CLIENT
        # --------------------------------------------------

        print(
            f"Initializing Gemini model: "
            f"{self.model_name}"
        )

        self.client = genai.Client(
            api_key=self.api_key
        )

        print(
            "Gemini client initialized successfully."
        )


    # ==========================================================
    # RETRIEVE CONTEXT
    # ==========================================================

    def retrieve_context(
        self,
        question: str,
        top_k: int | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks
        for the user's question.
        """

        results = self.retriever.retrieve(
            query=question,
            top_k=self.top_k if top_k is None else top_k,
        )

        return results


    # ==========================================================
    # BUILD CONTEXT
    # ==========================================================

    def build_context(
        self,
        retrieved_chunks: List[Dict[str, Any]],
    ) -> str:
        """
        Convert retrieved chunks into
        structured context for Gemini.
        """

        if not retrieved_chunks:
            return ""

        context_parts = []

        for index, chunk in enumerate(
            retrieved_chunks,
            start=1,
        ):

            section_id = chunk.get(
                "section_id",
                "Unknown",
            )

            section_title = chunk.get(
                "section_title",
                "Unknown",
            )

            content = chunk.get(
                "content",
                "",
            )

            similarity = chunk.get(
                "similarity",
                0.0,
            )

            context_part = f"""
SOURCE {index}

Section ID: {section_id}

Section Title: {section_title}

Similarity Score: {similarity:.4f}

Document Content:
{content}
"""

            context_parts.append(
                context_part.strip()
            )

        return "\n\n".join(context_parts)


    # ==========================================================
    # BUILD PROMPT
    # ==========================================================

    def build_prompt(
        self,
        question: str,
        context: str,
    ) -> str:
        """
        Build a grounded RAG prompt.
        """

        prompt = f"""
You are an AI assistant designed to answer questions
about a Detailed Project Report (DPR).

Your job is to answer the user's question using ONLY
the document context provided below.

STRICT RULES:

1. Use ONLY the provided document context.

2. Do NOT use outside knowledge.

3. Do NOT invent facts, numbers, locations,
   names, or technical details.

4. If the answer is not available in the
   provided context, respond exactly:

   "I could not find this information in the provided DPR."

5. Give a clear and concise answer.

6. When relevant, mention the Section ID
   or Section Title.

7. Do NOT mention:
   - embeddings
   - vector databases
   - chunks
   - similarity scores
   - RAG systems
   - retrieved documents

8. Do not assume that information is correct
   merely because it appears in multiple sources.
   Answer only based on the information provided.

9. If multiple sources provide different information,
   clearly mention the inconsistency instead of
   inventing a resolution.

--------------------------------------------------
DOCUMENT CONTEXT
--------------------------------------------------

{context}

--------------------------------------------------
USER QUESTION
--------------------------------------------------

{question}

--------------------------------------------------
ANSWER
--------------------------------------------------
"""

        return prompt.strip()


    # ==========================================================
    # GET SOURCES
    # ==========================================================

    def get_sources(
        self,
        retrieved_chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Extract clean source information.
        """

        sources = []

        seen_chunk_ids = set()

        for chunk in retrieved_chunks:

            chunk_id = chunk.get(
                "chunk_id",
                "",
            )

            # Avoid duplicate chunks

            if chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(
                chunk_id
            )

            source = {

                "chunk_id": chunk_id,

                "section_id": chunk.get(
                    "section_id",
                    "Unknown",
                ),

                "section_title": chunk.get(
                    "section_title",
                    "Unknown",
                ),

                "similarity": round(
                    chunk.get(
                        "similarity",
                        0.0,
                    ),
                    4,
                ),

            }

            sources.append(
                source
            )

        return sources


    # ==========================================================
    # GENERATE LLM RESPONSE
    # ==========================================================

    def generate_llm_response(
        self,
        prompt: str,
    ) -> str:
        """
        Send the RAG prompt to Gemini
        and return the generated answer.
        """

        try:

            print(
                "\nSending request to Gemini..."
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            answer = response.text

            if not answer:
                return (
                    "I could not generate an answer "
                    "from the provided DPR."
                )

            return answer.strip()


        except Exception as error:

            print(
                f"\nGemini Error: {error}"
            )

            return (
                "An error occurred while generating "
                "the answer."
            )


    # ==========================================================
    # MAIN RAG PIPELINE
    # ==========================================================

    def generate(
        self,
        question: str,
        top_k: int | None = None,
    ) -> Dict[str, Any]:
        """
        Complete RAG Pipeline.

        Question
            ↓
        Retrieval
            ↓
        Context Building
            ↓
        Prompt Building
            ↓
        Gemini Generation
            ↓
        Final Answer
        """

        # --------------------------------------------------
        # VALIDATE QUESTION
        # --------------------------------------------------

        if not question or not question.strip():

            raise ValueError(
                "Question cannot be empty."
            )

        if top_k is not None and top_k <= 0:
            raise ValueError("top_k must be greater than zero.")


        print("\n" + "=" * 60)
        print("STARTING RAG PIPELINE")
        print("=" * 60)

        print("\nQuestion:")
        print(question)


        # ==================================================
        # STEP 1: RETRIEVE DOCUMENT CONTENT
        # ==================================================

        print("\n" + "-" * 60)
        print(
            "STEP 1: RETRIEVING RELEVANT "
            "DOCUMENT CONTENT"
        )
        print("-" * 60)

        retrieved_chunks = self.retrieve_context(
            question,
            top_k=top_k,
        )

        print(
            f"\nRetrieved chunks: "
            f"{len(retrieved_chunks)}"
        )


        # --------------------------------------------------
        # HANDLE NO RESULTS
        # --------------------------------------------------

        if not retrieved_chunks:

            answer = (
                "I could not find this information "
                "in the provided DPR."
            )

            return {

                "question": question,

                "answer": answer,

                "sources": [],

                "retrieved_chunks": [],

                "context": "",

                "prompt": "",

            }


        # ==================================================
        # STEP 2: BUILD DOCUMENT CONTEXT
        # ==================================================

        print("\n" + "-" * 60)
        print("STEP 2: BUILDING DOCUMENT CONTEXT")
        print("-" * 60)

        context = self.build_context(
            retrieved_chunks
        )

        print(
            f"\nContext characters: "
            f"{len(context)}"
        )


        # ==================================================
        # STEP 3: BUILD RAG PROMPT
        # ==================================================

        print("\n" + "-" * 60)
        print("STEP 3: BUILDING RAG PROMPT")
        print("-" * 60)

        prompt = self.build_prompt(
            question=question,
            context=context,
        )

        print(
            f"\nPrompt characters: "
            f"{len(prompt)}"
        )


        # ==================================================
        # STEP 4: GENERATE ANSWER WITH GEMINI
        # ==================================================

        print("\n" + "-" * 60)
        print("STEP 4: GENERATING ANSWER WITH GEMINI")
        print("-" * 60)

        answer = self.generate_llm_response(
            prompt
        )


        # ==================================================
        # STEP 5: PREPARE SOURCES
        # ==================================================

        sources = self.get_sources(
            retrieved_chunks
        )


        # ==================================================
        # FINAL RESULT
        # ==================================================

        result = {

            "question": question,

            "answer": answer,

            "sources": sources,

            "retrieved_chunks":
                retrieved_chunks,

            "context": context,

            "prompt": prompt,

        }


        print("\n" + "=" * 60)
        print("RAG PIPELINE COMPLETE")
        print("=" * 60)

        return result


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("TESTING RAG + GEMINI")
    print("=" * 60)


    # ======================================================
    # INITIALIZE RAG GENERATOR
    # ======================================================

    generator = RAGGenerator(

        top_k=5,

        embedding_model_name=
            "all-MiniLM-L6-v2",

        embeddings_path=
            "data/processed/"
            "DPR of Road_embeddings.json",

        model_name=
            "gemini-2.5-flash",

    )


    # ======================================================
    # TEST QUESTION
    # ======================================================

    question = (
        "What is the proposed road alignment?"
    )


    # ======================================================
    # RUN RAG PIPELINE
    # ======================================================

    result = generator.generate(
        question
    )


    # ======================================================
    # DISPLAY FINAL ANSWER
    # ======================================================

    print("\n" + "=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)

    print("\nQuestion:")

    print(
        result["question"]
    )

    print("\nAnswer:")

    print(
        result["answer"]
    )


    # ======================================================
    # DISPLAY SOURCES
    # ======================================================

    print("\n" + "=" * 60)
    print("SOURCES")
    print("=" * 60)


    if not result["sources"]:

        print(
            "\nNo sources found."
        )

    else:

        for index, source in enumerate(
            result["sources"],
            start=1,
        ):

            print(
                "\n" + "-" * 60
            )

            print(
                f"SOURCE #{index}"
            )

            print(
                f"Section ID: "
                f"{source['section_id']}"
            )

            print(
                f"Section Title: "
                f"{source['section_title']}"
            )

            print(
                f"Similarity: "
                f"{source['similarity']}"
            )


    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)