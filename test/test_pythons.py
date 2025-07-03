import os
import subprocess

if __name__ == "__main__":
    # Check if the 'out' directory exists, if not, create it
    output_dir = "test_out/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cur_path = os.path.dirname(os.path.abspath(__file__))
    ROOT = cur_path[:cur_path.rfind("py2cpp") + len("py2cpp")]

    total_files = 0
    for file in os.listdir(f"{ROOT}/test_pythons"):
        if file.endswith(".py"):
            print(f"Executing {file}...")
            result = subprocess.run(
                ["python", "main.py", f"test_pythons/{file}", f"{output_dir}{file[:-3]}.cpp"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"Error running {file}: {result.stderr}")
            total_files += 1
            print(f"Output of {file}:\n{result.stdout}")

    print(f"All {total_files} Python files in {output_dir} executed successfully.")


