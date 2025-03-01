import datetime
import logging
import math
import os
import sys
import threading
import time
import psycopg2
import datetime
import requests
from bs4 import BeautifulSoup

if not os.path.isdir("logs"):
    os.mkdir("logs")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/{datetime.datetime.now().timestamp()}telegram_bot.log')
    ]
)

logger = logging.getLogger(__name__)


class Subj:
    def __init__(self, name: str, base_url: str, login: str = None, password: str = None):
        session = requests.Session()
        self.loginname, self.password = login, password
        self.name: str = name
        self.session: requests.Session = session
        self.base_url: str = base_url
        self.subj_url: str = base_url.replace("://", f"://{name}.")
        self.problems: list[Problem] = []
        if login and password:
            if not self.login(login, password, self.subj_url):
                raise Exception("Login failed")

    def add_problem(self, problem):
        self.problems.append(problem)

    @classmethod
    def from_url(cls, url):
        name = url.split("://")[-1].split(".")[0]
        base_url = url.replace(f"://{name}.", "://")
        return cls(name, base_url)

    def add_problem_by_id(self, problem_id):
        problem = Problem.from_subj_and_id(self, problem_id)
        self.add_problem(problem)

    def login(self, login, password, subj_url):
        ans = self.session.post(f"{subj_url}/newapi/login", json={"guest": False, "password": password, "user": login})
        if ans.status_code != 200:
            return False

        if ans.json()["status"] is not True:
            return False

        return True

class ProblemHacker(Subj):
    def __init__(self, bd_conn: str, name: str, base_url: str, login: str = None, password: str = None):
        super().__init__(name, base_url, login, password)
        self.conn = psycopg2.connect(bd_conn)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS problems 
                                (secret_id INTEGER PRIMARY KEY, public_id INTEGER, subj_url TEXT)""")
        self.conn.commit()
        self.conn_url = bd_conn
        self.hack_threads: list[threading.Thread] = []

    def get_public_by_secret_id(self, secret_id):
        self.cursor.execute("SELECT public_id FROM problems WHERE secret_id=%s", (secret_id,))
        problem_id = self.cursor.fetchone()
        if not problem_id:
            return False

        problem_id = problem_id[0]
        return problem_id

    def get_problem_by_secret(self, secret_id):
        problem_id = self.get_public_by_secret_id(secret_id)
        if not problem_id:
            return False

        return Problem(self.name, self.base_url, problem_id)

    def hack_subj(self, subj: Subj, stop_num: int = 10000):
        threads = []
        for i in range(0, stop_num, stop_num//10):
            t = threading.Thread(target=self.problems_hacker, args=(subj.subj_url, i, min(i+stop_num/10, stop_num)))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def problems_hacker(self, subj_url, start_num, stop_num = None):
        conn = psycopg2.connect(self.conn_url)
        cursor = conn.cursor()
        a = start_num
        if not stop_num:
            stop_num = math.inf
        while a < stop_num:
            url = f"{subj_url}/problem?id={a}"

            response = self.session.get(url)
            parser = BeautifulSoup(response.text, "html.parser")
            problem = parser.find(class_="prob_maindiv")
            if not problem:
                a += 1
                continue

            problem_num = problem.get("id").replace("maindiv", "")
            cursor.execute("SELECT secret_id FROM problems WHERE secret_id = %s", (problem_num,))
            time.sleep(0.1)
            if cursor.fetchone() is not None:
                a += 1
                continue

            self.save_problem(problem_num, a, subj_url, cursor, conn)
            a += 1

    def save_problem(self, secret_id, public_id, subj_url, cursor = None, conn = None):
        print(secret_id, public_id)
        if not cursor or not conn:
            cursor = self.cursor
            conn = self.conn
        cursor.execute("INSERT INTO problems (secret_id, public_id, subj_url) VALUES (%s, %s, %s)",
                            (secret_id, public_id, subj_url))
        conn.commit()

    def update_problems(self, subj_url, stop_num):
        self.cursor.execute("DELETE FROM problems WHERE subj_url = %s", (subj_url, ))
        self.hack_subj(subj_url, stop_num)


class Problem(Subj):
    def __init__(self, name: str, base_url: str, problem_id: str | int, login: str = None, password: str = None):
        super().__init__(name, base_url, login, password)
        problem_id = str(problem_id)
        self.problem_id = problem_id
        self.problem_url = self.subj_url+'/problem?id='+problem_id
        self.problem_secret_id = self.problem_secret_id()
        self.problem_answer = self.get_problem_answer()

    def problem_secret_id(self) -> str | bool:
        ans = self.session.get(self.problem_url)
        if ans.status_code != 200:
            raise Exception(f"Failed to load problem page. Status code: {ans.status_code}")

        parser = BeautifulSoup(ans.text, "html.parser")
        problem = parser.find(class_="prob_maindiv")
        if not problem:
            return False

        problem_secret_id = problem.get("id").replace("maindiv", "")
        return problem_secret_id

    def get_problem_answer(self) -> str | bool:
        ans = self.session.get(self.problem_url)
        if ans.status_code != 200:
            raise Exception(f"Failed to load problem page. Status code: {ans.status_code}")

        parser = BeautifulSoup(ans.text, "html.parser")
        problem = parser.find(class_="answer")
        if not problem:
            return False

        problem_answer = problem.find("span").text.replace("Ответ: ", "")
        return problem_answer

    @classmethod
    def from_url(cls, url, login: str = None, password: str = None):
        name = url.split("://")[-1].split(".")[0]
        base_url = url.replace(f"://{name}.", "://")
        base_url = base_url[:base_url.rfind("/")]
        problem_id = url.split("id=")[-1]
        return cls(name, base_url, problem_id, login, password)

    @classmethod
    def from_subj_and_id(cls, subj: Subj, problem_id: int | str, login: str = None, password: str = None):
        return cls(subj.name, subj.base_url, problem_id, login, password)

class Test(Subj):
    def __init__(self, name: str, base_url: str, test_id: str | int, login: str = None, password: str = None):
        super().__init__(name, base_url, login, password)
        test_id = str(test_id)
        self.test_id = test_id
        self.test_url = self.subj_url + '/test?id=' + test_id
        self.problems = {}
        self.test_session = ""
        self.continue_url = ""
        self.problem_types = {}
        self.load_test()


    @classmethod
    def from_url(cls, url, login: str = None, password: str = None):
        name = url.split("://")[-1].split(".")[0]
        base_url = url.replace(f"://{name}.", "://")
        base_url = base_url[:base_url.rfind("/")]
        test_id = url.split("id=")[-1]
        return cls(name, base_url, test_id, login, password)

    @classmethod
    def from_subj_and_id(cls, subj: Subj, test_id: int | str, login: str = None, password: str = None):
        return cls(subj.name, subj.base_url, test_id, login, password)

    def load_test(self):
        ans = self.session.get(self.test_url)
        if ans.status_code!= 200:
            raise Exception(f"Failed to load test page. Status code: {ans.status_code}")

        text = ans.text
        self.test_session = self.extract_test_session(text)
        self.problems = self.extarct_problems_ids(text)
        self.continue_url = self.test_url + f"&continue={self.test_session}"
        self.problem_types = self.extract_types(text)

    def extract_test_session(self, test_text):
        parser = BeautifulSoup(test_text, "html.parser")
        test_session = parser.find(attrs={'name': "stat_id"})
        if not test_session:
            raise Exception("Test session not found")
        test_session = test_session.get("value")
        return test_session

    def extarct_problems_ids(self, test_text):
        parser = BeautifulSoup(test_text, "html.parser")
        problems = parser.find_all("div", class_="prob_maindiv")
        problems_ids = {}
        for problem in problems:
            problems_ids[problem.get("data-num")] = problem.get("data-id")
        return problems_ids

    def extract_types(self, test_text):
        parser = BeautifulSoup(test_text, "html.parser")
        problems = parser.find_all("div", class_="prob_view")
        problem_types_dict = {}
        for problem in problems:
            input_type = problem.find(class_="test_inp")
            if not input_type:
                continue

            data = input_type.get("name").split("_")
            type = "detail" if "c" in data[2] else "simple"
            problem_types_dict[data[1]] = type

        return problem_types_dict

    def save_answer(self, problem_num, answer):
        data = {
            "stat_id": self.test_session,
            "answer[]": answer,
            "name": f"answer_{problem_num}_{self.problems[problem_num]}"
        }
        ans = self.session.post(f"{self.subj_url}/test", params={"a": "save_part", "ajax": "1"}, data=data)
        if ans.status_code != 200 or ans.text != "ok" + answer:
            raise Exception(f"Failed to save answer. Status code: {ans.status_code}")

        print(f"Answer for problem {problem_num} saved successfully")

    def solve(self):
        detailed_answers = {}
        hacker = ProblemHacker(os.getenv('POSTGRES_CONN'), self.name, self.base_url, self.loginname, self.password)
        for problem in self.problems.items():
            num, secret = problem
            problem = hacker.get_problem_by_secret(secret)
            if not isinstance(problem, Problem):
                continue

            if self.problem_types[num] == "detail":
                detailed_answers[num] = problem.problem_url

            answer = problem.problem_answer
            if not isinstance(answer, str):
                continue
            self.save_answer(num, answer)

        return detailed_answers

    def get_problems_answers(self):
        ans = {}
        hacker = ProblemHacker(os.getenv('POSTGRES_CONN'), self.name, self.base_url, self.loginname, self.password)
        for problem in self.problems.items():
            num, secret = problem
            problem = hacker.get_problem_by_secret(secret)
            if not isinstance(problem, Problem):
                continue

            answer_url = problem.problem_url
            if not isinstance(answer_url, str):
                continue

            answer = problem.problem_answer
            if not isinstance(answer, str):
                continue

            ans[num] = (answer, answer_url)
        return ans





if __name__ == '__main__':
    args = sys.argv[1:]
    for arg in args:
        if arg.startswith("--target="):
            target = arg.replace("--target=", "")
            if target == "hack":
                hacker = ProblemHacker(os.getenv("POSTGRES_CONN"), name="math8-vpr", base_url="https://sdamgia.ru")
                hacker.hack_subj(subj=hacker, )
                break

            elif target == "get":
                hacker = ProblemHacker(os.getenv("POSTGRES_CONN"), name="math8-vpr", base_url="https://sdamgia.ru")
                for arg in args:
                    if arg.startswith("--test_num="):
                        test_num = int(arg.replace("--test_num=", ""))
                        print(hacker.get_public_by_secret_id("949963"))
                        break

                break

            elif target == "solve":
                hacker = ProblemHacker(os.getenv("POSTGRES_CONN"), name="math8-vpr", base_url="https://sdamgia.ru")
                for arg in args:
                    if arg.startswith("--test_url="):

                        test_url = arg.replace("--test_url=", "")
                        test = Test.from_url(test_url, os.getenv("USER"), os.getenv("PASSWORD"))
                        print(test.get_problems_answers())
                        print(test.solve())
                        print(test.continue_url)
                        break

                break
