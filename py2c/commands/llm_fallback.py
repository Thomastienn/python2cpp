import ast

from py2c.utils.utils import Utils
from py2c.utils.logger import setup_logger


def LLMParser(parse_func):
    def wrapper(tree):
        logger = setup_logger("py2cpp.parser.fallback")
        try:
            cpp_output = Utils.capture_output(parse_func, tree)
            logger.info("Parsing using ast succeeded.")
            print(cpp_output)
        except Exception as e:
            logger.error(f"Parse using ast failed: {e}")
            # Attempt to use LLM to fix the errors
            logger.info("Falling back to LLM for parsing...")

            # Lazy imports — only loaded when LLM fallback is actually needed.
            # This avoids crashing at import time on environments where
            # google-genai or GOOGLE_API_KEY may not be available (e.g. Vercel
            # cold starts for the /convert endpoint which doesn't need LLM).
            from dotenv import load_dotenv
            from google import genai
            from google.genai import types
            from py2c.core.structure import LLMFixResponse

            load_dotenv()
            client = genai.Client()

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    "Convert the following Python code to C++ :\n\n" + ast.unparse(tree)
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    system_instruction="You are a Python to C++ converter. You will be given a Python code and you need to convert it to C++ code. Make sure there is no compile error, syntax error, or logic error in the code. Do not add extra comments or explanations, just return the C++ code.",
                    response_mime_type="application/json",
                    response_schema=LLMFixResponse,
                ),
            )
            llm_response: LLMFixResponse = response.parsed
            if llm_response.code:
                print(llm_response.code)
            else:
                print("LLM failed to fix")
        finally:
            logger.info("Parsing completed")

    return wrapper
