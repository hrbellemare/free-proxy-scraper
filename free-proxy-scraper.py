# File: free-proxy-scraper.py
# Author: Harry Bellemare
# Date: 2022-09-05
# Description: Validates proxies from https://free-proxy-list.net/ & exports them to Excel with their working status.

import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple, List, Generator, Callable
from functools import wraps
import time


def timing(f) -> Callable:
    """
    Decorator that prints the execution time of a function.
    From Jonathan Prieto-Cubides on StackOverflow: https://stackoverflow.com/a/27737385
    :param f:
    :return:
    """

    @wraps(f)
    def wrap(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        print(f"func:{f.__name__} args:[{args}, {kw}] took: {te - ts} sec")
        return result

    return wrap


class Proxy(NamedTuple):
    ip: str
    port: str
    country: str
    anonymity: str
    https: str
    last_checked: str


def running_feedback() -> Generator:
    """
    Give the user visual feedback that the script is doing something.
    """
    while True:
        yield from "|/-\\"


def fetch_proxies() -> List[Proxy]:
    """
    Fetch proxy data from https://free-proxy-list.net/
    :return: List of Proxy objects
    """
    url = "https://free-proxy-list.net/"
    # TODO: Allow the user to pick from a list of proxy sites to scrape.
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", attrs={"class": "table table-striped table-bordered"})
    proxies = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        proxy = Proxy(
            ip=cols[0].text,
            port=cols[1].text,
            country=cols[3].text,
            anonymity=cols[4].text,
            https=cols[6].text,
            last_checked=cols[7].text,
        )
        proxies.append(proxy)
    return proxies


# A side-benefit of the timing decorator is that it helps us visualize the data flow of the program.
@timing
def check_proxy(proxy: Proxy) -> (Proxy, str):
    """
    Check if a proxy is working.
    :param proxy: a Proxy namedtuple
    :return: a Proxy namedtuple with the status appended
    """
    try:
        response = requests.get(
            "https://www.google.com",
            proxies={"https": f"{proxy.ip}:{proxy.port}"},
            timeout=5,
        )
        # status code 200 = OK
        if response.status_code == 200:
            return proxy, "working"
        else:
            return proxy, "not working"
    except requests.exceptions.RequestException:
        return proxy, "not working"


@timing
def export_sorted_df(df: pd.DataFrame, file_name: str) -> None:
    """
    Sorts a DataFrame by the 'status' column, then exports it to Excel.
    :param df: a DataFrame
    :param file_name: the name of the Excel file
    """

    def datetime_string() -> str:
        """
        :return: a date/time string suitable for the Excel file name.
        """
        return time.strftime("%Y_%m_%d_%H%M", time.localtime())

    # Sort the DataFrame by the status column ('working' first)
    df.sort_values(by="status", inplace=True, ascending=False)
    # Save the DataFrame to an Excel file
    df.to_excel(f"{file_name}_{datetime_string()}.xlsx", index=False)


@timing
def main() -> None:
    feedback = running_feedback()
    proxies = fetch_proxies()
    print(f"Found {len(proxies)} proxies.")

    # Conduct the checks in parallel using a ThreadPoolExecutor.
    with ThreadPoolExecutor(max_workers=100) as executor:
        for i, (proxy, status) in enumerate(executor.map(check_proxy, proxies)):
            print(f"\rChecking proxies... {next(feedback)}", end="")
            proxies[i] = (proxy, status)
            if i % 10 == 0:
                print(f"\rChecking proxies... {next(feedback)}", end="")
    print("\nDone.")

    print("Exporting to Excel...")

    # Unpack the values returned by check_proxy()
    proxies, statuses = zip(*proxies)

    # Create a DataFrame from the scraped data, then add the statuses
    df = pd.DataFrame(proxies)
    df["status"] = statuses

    # Export the DataFrame to Excel
    export_sorted_df(df, "freeproxylist")


if __name__ == "__main__":
    main()
