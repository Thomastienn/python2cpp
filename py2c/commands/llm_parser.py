import ast

from google import genai
from google.genai import types
from dotenv import load_dotenv

from py2c.core.structure import LLMFixResponse
from py2c.utils.utils import Utils
from py2c.utils.logger import setup_logger

load_dotenv()


def LLMParser(parse_func):
    """
    Decorator to handle fallback parsing using LLM when the initial parse fails. Or compile errors that is not expected.
    """
    def wrapper(tree):
        """
        Fallback to use llm to fix the rest of the compile errors.

        Args:
            tree (ast.AST): The Python Abstract Syntax Tree to convert

        Returns:
            None: The function prints the converted C++ code to stdout

        """
        logger = setup_logger("py2cpp.parser.fallback")
        client = genai.Client()
        try:
            logger.info("Attempting to parse using ast...")
            cpp_output: str = Utils.capture_output(parse_func, tree)
            logger.info("Parsing using ast succeeded. Using llm to check and fix the code...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=["Here is your c++ code:\n\n" + cpp_output],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    system_instruction="You are a C++ expert. You will be given a C++ code and you need to check if there is any compile error, syntax error, or logic error in the code. If there is any, fix it and return the final cpp file content. Otherwise, leave it as is (None).",
                    response_mime_type="application/json",
                    response_schema=LLMFixResponse,
                )
            )
            logger.info("LLM response received. Printing the response...")
            llm_response: LLMFixResponse = response.parsed
            if llm_response.code:
                print(cpp_output)
            else:
                print(llm_response.code)
        except Exception as e:
            logger.error(f"Parse using ast failed: {e}")
            # Attempt to use LLM to fix the errors
            logger.info("Falling back to LLM for parsing...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=["Convert the following Python code to C++ :\n\n" + ast.unparse(tree)],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    system_instruction="You are a Python to C++ converter. You will be given a Python code and you need to convert it to C++ code. Make sure there is no compile error, syntax error, or logic error in the code.",
                    response_mime_type="application/json",
                    response_schema=LLMFixResponse,
                )
            )
            llm_response: LLMFixResponse = response.parsed
            if llm_response.code:
                print(llm_response.code)
            else:
                print("LLM failed to fix")
        finally:
            logger.info("Parsing completed")

    return wrapper
