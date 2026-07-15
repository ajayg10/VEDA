import unittest

from core.code_agent.generation import PythonModuleGenerator


class PythonModuleGeneratorTests(unittest.TestCase):
    def test_generates_a_valid_function_scaffold(self):
        code = PythonModuleGenerator().generate_function("calculate", ["amount", "rate"], "Calculate total.")

        compile(code, "generated.py", "exec")
        self.assertIn('"""Calculate total."""', code)
        self.assertIn("raise NotImplementedError", code)

    def test_rejects_invalid_python_names(self):
        with self.assertRaises(ValueError):
            PythonModuleGenerator().generate_function("class", [], "")


if __name__ == "__main__":
    unittest.main()
