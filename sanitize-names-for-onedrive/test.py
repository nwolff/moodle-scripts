import unittest

from sanitize_names import sanitized_path_element


class SanitizePathElementTest(unittest.TestCase):
    def test_noop(self):
        self.assertEqual(sanitized_path_element("a"), "a")

    def test_all(self):
        self.assertEqual(
            sanitized_path_element("  a*b:c<d>e?f/g\h|i  "), "_ a_b_c_d_e_f_g_h_i _"
        )


if __name__ == "__main__":
    unittest.main()
