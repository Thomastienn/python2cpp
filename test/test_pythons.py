import os
import subprocess

if __name__ == "__main__":
    # Check if the 'out' directory exists, if not, create it
    if not os.path.exists("out/"):
        os.makedirs("out/")

    cur_path = os.path.dirname(os.path.abspath(__file__))
    ROOT = cur_path[:cur_path.rfind("py2cpp") + len("py2cpp")]

    for file in os.listdir(f"{ROOT}/test_pythons"):
        if file.endswith(".py"):
            print(f"Executing {file}...")
            result = subprocess.run(
                    ["python", "main.py", f"test_pythons/{file}", f"{file[:-3]}.cpp"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"Error running {file}: {result.stderr}")
            print(f"Output of {file}:\n{result.stdout}")
    
    print("All Python files in 'out/' executed successfully.")
                
            
