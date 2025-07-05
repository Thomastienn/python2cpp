import os
import subprocess
import unittest

class TestAllPythons(unittest.TestCase):
    pass  # we'll fill in test methods dynamically below

def _make_test(file, root, output_dir):
    """
    Return a test method that will run `main.py` on `file`
    and assert exit code == 0.
    """
    def test(self):
        src = os.path.join("test_pythons", file)
        dst = os.path.join(output_dir, file[:-3] + ".cpp")
        result = subprocess.run(
            ["python", "main.py", src, dst],
            capture_output=True, text=True
        )
        self.assertEqual(
            result.returncode, 0,
            msg=f"\n{file} failed:\n{result.stderr}"
        )
    return test

# --- Dynamically attach one test method per .py file ---
cur_path = os.path.dirname(os.path.abspath(__file__))
ROOT = cur_path[:cur_path.rfind("py2cpp") + len("py2cpp")]
test_dir = os.path.join(ROOT, "test_pythons")
output_dir = os.path.join(ROOT, "test_out")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

for fname in os.listdir(test_dir):
    if not fname.endswith(".py"):
        continue
    # make a valid method name: test_<basename>
    method_name = f"test_{fname[:-3]}"
    # create the function, binding fname, ROOT and output_dir
    test_method = _make_test(fname, ROOT, output_dir)
    setattr(TestAllPythons, method_name, test_method)

if __name__ == "__main__":
    unittest.main(verbosity=2)
