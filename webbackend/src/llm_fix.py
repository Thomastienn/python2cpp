import os
import ast
import time
import tempfile
import subprocess

from google import genai
from google.genai import types
from dotenv import load_dotenv

from py2c.core.structure import LLMFixResponse
from py2c.utils.utils import Utils
from py2c.utils.logger import setup_logger

load_dotenv()


def LLMFix(cpp_output: str):
    logger = setup_logger("py2cpp.parser.fix")

    # Compile and check the C++ errors and warnings
    with tempfile.TemporaryDirectory() as tempdir:
        cpp_filename = f"{Utils.generate_unique_filename("temp")}.cpp"
        out_filename = f"{Utils.generate_unique_filename("temp")}.out"

        cpp_file_path = os.path.join(tempdir, cpp_filename)
        out_file_path = os.path.join(tempdir, out_filename)

        with open(cpp_file_path, "w") as cpp_file:
            cpp_file.write(cpp_output)

        logger.info(f"Temporary C++ file created at {cpp_file_path}")
        logger.info("Compiling C++ code...")
        compile_command = [
            "g++", "-std=c++20", "-o", out_file_path, cpp_file_path
        ]
        result = subprocess.run(compile_command, capture_output=True, text=True)

        # Remove temporary files if they exist
        if os.path.exists(cpp_file_path):
            os.remove(cpp_file_path)
        if os.path.exists(out_file_path):
            os.remove(out_file_path)
        
        # No need to fix
        if result.returncode == 0:
            logger.info("Compilation successful. No errors found.")
            return cpp_output
        else:
            errors = result.stderr.strip()
            logger.info("Compilation failed with errors: \n" + errors)
            

    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            "Here is your c++ code:\n\n" + cpp_output,
            "Here are the compilation errors:\n\n" + errors
        ],
        config=types.GenerateContentConfig(
            temperature=0.0,
            system_instruction="You are a C++ expert. You will be given a C++ code and compilation errors and you need to fix all compile error, syntax error, any errors except logic errors in the code. Make sure the code is valid C++ code and can be compiled without any errors. Do not add extra comments or explanations, just return the fixed C++ code.",
            response_mime_type="application/json",
            response_schema=LLMFixResponse,
        )
    )
    logger.info("LLM fixed finished")
    llm_response: LLMFixResponse = response.parsed
    if not llm_response.code:
        logger.error("LLM failed to fix the code")
        raise Exception("LLM failed to fix the code")

    logger.info("LLM fixed the code successfully")
    logger.info("Fixed C++ code:\n" + llm_response.code)
    return llm_response.code

