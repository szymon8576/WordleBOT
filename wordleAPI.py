import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from time import sleep


"""
Class responsible for interaction with Wordle websites 
"""


class WordleAPI:

    def __init__(self, website="unlimited"):

        assert website in ["nyt", "unlimited"]

        self.driver = webdriver.Chrome('./chromedriver')
        self.website = website
        self.driver.get("https://www.nytimes.com/games/wordle" if website=="nyt" else "https://wordlegame.org/")
        self.last_ans_row = -1

        if website == "nyt":
            self.close_popups()

    def close_popups(self):
        assert self.website == "nyt"
        self.driver.find_element(By.ID, "pz-gdpr-btn-closex").click()
        self.driver.find_element(By.XPATH, "//div[@class='Modal-module_closeIcon__b4z74']").click()

    def send_answer(self, word):
        assert len(word) == 5, word

        tile = self.driver.find_element(By.TAG_NAME, "body")
        tile.send_keys(word)
        sleep(1)
        tile.send_keys(Keys.ENTER)
        sleep(1)
        self.last_ans_row += 1

    def get_state(self):
        state = []

        if self.website == "nyt":
            tiles = self.driver.find_elements(By.XPATH, "//div[(@data-testid='tile') and (@class='Tile-module_tile__3ayIZ')]")

            for i, tile in enumerate(list(tiles)[self.last_ans_row * 5: self.last_ans_row * 5 + 5]):
                state += [tile.get_attribute("data-state")]

        else:
            tiles = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'Row-letter')]")

            for i, tile in enumerate(list(tiles)[self.last_ans_row * 5: self.last_ans_row * 5 + 5]):

                state_info = tile.get_attribute("class").replace("elsewhere", "present").split("-")[-1]
                state += [state_info]

        return state

    def erase_word(self):
        tile = self.driver.find_element(By.TAG_NAME, "body")
        for _ in range(5):
            tile.send_keys(Keys.BACKSPACE)
        sleep(2)



