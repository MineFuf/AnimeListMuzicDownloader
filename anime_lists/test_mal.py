import unittest
from .mal import Mal

class TestMal(unittest.TestCase):
    def test_user_exists(self):
        self.assertEqual(Mal.check_username('morsee31'), True)
        
    def test_user_does_not_exist(self):
        self.assertEqual(Mal.check_username('morsee31113'), False)
        