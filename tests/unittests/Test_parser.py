import os
import unittest
from app.sdamgia_hack.parser import Parser
from dotenv import load_dotenv


class ParserPreparation(unittest.TestCase):
    def setUp(self):
        self.parser = Parser(base_url="https://sdamgia.ru")


    def test_extraction_num_and_subj(self):
        url = "https://math8-vpr.sdamgia.ru/test?id=2542233"
        url_excepted = "https://math8-vpr.sdamgia.ru/test"
        subj_url_expected = "https://math8-vpr.sdamgia.ru"
        url_res, subj, num, subj_url = self.parser.get_url_data(test_url=url)
        self.assertEqual(url_excepted, url_res)
        self.assertEqual(num, 2542233)
        self.assertEqual(subj, "math8-vpr")
        self.assertEqual(subj_url, subj_url_expected)

    def test_creating_url(self):
        subj = "math8-vpr"
        test_num = 2542233
        subj_url_expected = "https://math8-vpr.sdamgia.ru"
        expected_url = f"https://math8-vpr.sdamgia.ru/test"
        url, res_subj, res_num, subj_url = self.parser.get_url_data(test_num=test_num, subj=subj)
        self.assertEqual(expected_url, url)
        self.assertEqual(res_subj, subj)
        self.assertEqual(res_num, test_num)
        self.assertEqual(subj_url, subj_url_expected)

class TestLogin(unittest.TestCase):
    def setUp(self):
        load_dotenv()
        self.parser = Parser(base_url="https://sdamgia.ru")

    def test_login_correct(self):
        username = os.getenv('USER')
        password = os.getenv("PASSWORD")
        subj = "https://math8-vpr.sdamgia.ru"
        ans = self.parser.login(login=username, password=password, subj_url=subj)
        self.assertEqual(ans, True)

    def test_login_incorrect(self):
        username = "test@mail.ru"
        password = "test"
        subj = "https://math8-vpr.sdamgia.ru"
        ans = self.parser.login(login=username, password=password, subj_url=subj)
        self.assertEqual(ans, False)

if __name__ == '__main__':
    unittest.main()
