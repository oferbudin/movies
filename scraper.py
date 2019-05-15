from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import datetime
import json
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


def randomized_user_agent():
    # Return web_driver options with a header of a randomized user agent
    ua = UserAgent()
    user_agent = ua.random
    opts = Options()
    opts.add_argument("user-agent=[%s]" % user_agent)
    return opts


class RavHenScraper:

    # Class attributes hold data regarding each site's code for building proper url, and name to be entered to bank.json
    HERZLYIA = ("1061", "Rav_Hen_Herzlyia")
    GIVATAYIM = ("1058", "Rav_Hen_Givatayim")
    DIZINGOF = ("1071", "Rav_Hen_Dizingof")
    MODIIN = ("1069", "Rav_Hen_Modiin")
    KIRYAT_ONO = ("1062", "Rav_Hen_Kiryat_Ono")

    @classmethod
    def get_current_movies_screens_url(cls, city_code):
        url = "https://www.rav-hen.co.il/#/buy-tickets-by-cinema?in-cinema=%s&at=%s&view-mode=list" % (city_code, datetime.date.today())
        return url

    @classmethod
    def load_website_data_to_json(cls, website):
        driver = webdriver.Chrome(options=randomized_user_agent())
        driver.get(RavHenScraper.get_current_movies_screens_url(website[0]))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        movies_dict = {}
        # Iterate over each "block" - containing a movie's name, screens time and urls of links to orders
        movies_blocks = soup.find_all("div", attrs={"class": ["row movie-row", "row movie-row first-movie-row"]})
        for movie_block in movies_blocks:
            movie_name = str(movie_block).split('name">')[1].split('</')[0]
            movies_dict[movie_name] = {}
            screens_data = str(movie_block).replace("amp;", "").split('data-url="')[1:]
            for screen in screens_data:
                data = screen.split('" href="#">')
                screen_url = data[0]
                screen_time = data[1][:5]
                movies_dict[movie_name][screen_time] = screen_url
        driver.close()
        # Update the bank.json with the updated movies_dict
        with open("bank.json", "r") as json_file:
            data = json.load(json_file)
            data[website[1]] = movies_dict
        with open("bank.json", "w") as outfile:
            json.dump(data, outfile)

    @classmethod
    def go_to_screen(cls, website, movie_name, screen_time, tickets):
        # Gets you all the way to page of choosing seats for a certain movie screen.
        # This driver will be activated by the user's regquest.
        active_driver = webdriver.Chrome(options=randomized_user_agent())
        with open("bank.json", "r") as json_file:
            data = json.load(json_file)
        try:
            active_driver.get(data[website[1]][movie_name][screen_time])
        except KeyError:
            raise SystemError("I don't know this screen: '%s' at '%s'" % (movie_name, screen_time))
        # Select tickets quantity and enter the choosing seats screen
        active_driver.find_element_by_xpath('//select[@class="ddlTicketQuantity"]/option[@value="%s"]' % str(tickets)).click()
        active_driver.find_element_by_xpath('//a[@id="lbSelectSeats"]').click()
        # Return the page source code, which holds data regarding the seats in this movie screen
        return active_driver.page_source

    @classmethod
    def parse_soup_seats(cls, page_source):
        # Parse seats data from the 'choosing seats' page to our needed seats_db dict.
        soup = BeautifulSoup(page_source, "html.parser")
        # Enter the accesibleSeatPlanContainer
        seats_raw_data = soup.find("div", attrs={"id": "accesibleSeatPlanContainer"})
        seats_splitted_raw_list = str(seats_raw_data).split('td_')[1:]
        seats_splitted_parsed_list = []
        # Parse the seats_splitted_raw_list:
        valid_char = [str(i) for i in range(50)] + ["_"]
        seat_offset = 0
        line_offset = 0
        line_info = lambda seat_str: int("".join([char for char in list(seat_str[:5]) if char in valid_char]).split("_")[0])
        # Iterate over each line's (fake / real) seat in the theater
        for seat in seats_splitted_raw_list:

            # Re-initializing offset when needed:
            line = line_info(seat)
            if seats_splitted_raw_list.index(seat) == 0:
                # First run, no former seats to compare, there should be no offset
                seat_offset = 0
            elif line != line_info(seats_splitted_raw_list[seats_splitted_raw_list.index(seat) - 1]):
                # This seat element is from a new line in the iteration, offset should be re-initialized
                seat_offset = 0
                # update line offset (and never re-initialize)
                line_offset += line - line_info(seats_splitted_raw_list[seats_splitted_raw_list.index(seat) - 1]) - 1

            # Parsing the seat data and adding to 'seats_splitted_parsed_list'
            try:
                actual_data = seat.split('id="s_')[1]
                website_seat_line = "".join([char for char in list(actual_data[:5]) if char in valid_char]).split("_")
                real_seat_line = [int(element) for element in website_seat_line]
                real_seat_line = [real_seat_line[0] - seat_offset, real_seat_line[1] - line_offset]
                seat_state = "".join(seat.split('data-state="')[1][:1])
                seats_splitted_parsed_list.append((real_seat_line[1], line_offset, real_seat_line[0], seat_state, seat_offset))
            except IndexError:
                # this is not a real seat in the line
                seat_offset += 1
                continue

        # Create the parsed_seats_dict
        last_line = seats_splitted_parsed_list[-1][0]
        parsed_seats_dict = {}
        for i in range(1, last_line + 1):
            parsed_seats_dict[i] = {"line_offset": None, "seats": {}}
        for seat in seats_splitted_parsed_list:
            parsed_seats_dict[seat[0]]["line_offset"] = seat[1]
            parsed_seats_dict[seat[0]]["seats"][seat[2]] = {"state": seat[3], "offset": seat[4]}

        return parsed_seats_dict


if __name__ == "__main__":

    print(RavHenScraper.parse_soup_seats(RavHenScraper.go_to_screen(RavHenScraper.HERZLYIA, "הנוקמים: סוף המשחק", "21:30", 10)))






