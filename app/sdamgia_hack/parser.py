import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(
    level=logging.INFO,  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
    handlers=[
        logging.FileHandler('app.log'),  # Логирование в файл
        logging.StreamHandler()  # Логирование в консоль
    ]
)

logger = logging.getLogger(__name__)


class Parser:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.session()


    def pars_test(self, test_num: int = None, subj: str = None, test_url: str = None):
        logger.info(f"parsing tests: test_num: {test_num}, subj: {subj}, test_url: {test_url}")
        url, subj, test_num, subj_url = self.get_url_data(test_num, subj, test_url)

        response = self.session.get(url, params={"id": test_num})
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes

        data = self.get_tests_data(response.text)

    def get_tests_data(self, html_content: str):
        parser = BeautifulSoup(html_content, "html.parser")
        data = parser.find_all("<div class=\"prob_view\" style=\"margin-bottom:30px\">")

    def login(self, login, password, subj_url):
        logger.info(f"Login subj_url: {subj_url} "
                    f"login: {login[:3]+"*"*(len(login)-3)} password: {password[:3]+"*"*(len(password)-3)}")

        ans = self.session.post(f"{subj_url}/newapi/login", json={"guest": False, "password": password, "user": login})
        if ans.status_code != 200:
            return False

        if ans.json()["status"] != True:
            return False

        return True

    def get_url_for_test(self, subj_url) -> str:
        logger.debug(f"Get url by subj_url: {subj_url}")
        url = f"{subj_url}/test"
        return url

    def get_subj_url(self, subj):
        logger.debug(f"Get subj_url by subj: {subj}")
        return self.base_url.replace("//", f"//{subj}.")

    def get_url_data(self, test_num: int = None, subj: str = None, test_url: str = None) -> tuple[str, str, int, str]:
        logger.info(f"getting url for data test_num: {test_num} subj: {subj} test_url: {test_url}")

        if (test_num is None or subj is None) and test_url is None:
            raise ValueError("Either test_num with subj or test_url must be provided.")

        if test_url is not None:
            subj = test_url.split('.')[0].split("//")[-1]
            test_num = int(test_url.split("?id=")[-1])

        subj_url = self.get_subj_url(subj)
        url = self.get_url_for_test(subj_url)

        return url, subj, test_num, subj_url

if __name__ == '__main__':
    parser = Parser("https://sdamgia.ru")
    parser.pars_test(test_num=155634, subj="inf8-vpr")
