# ObjSup by Alex

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
import time
import json
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
from termcolor import colored
from seleniumrequests import Chrome
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class ObjSup:
    def __init__(self):
        print
        self.start = time.time()
        with open('settings.json', 'r') as settingsFile:
            self.settings = json.loads(settingsFile.read())
        self.headers = {'Accept': '*/*',
                        'Accept-Encoding': 'gzip, deflate, sdch',
                        'Accept-Language': 'en-US,en;q=0.8',
                        'Cache-Control': 'max-age=0',
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.81 Safari/537.36'}
        self.session = Chrome('/Users/alex/PycharmProjects/FirstSelenium/chromedriver')
        self.session.headers = self.headers
        self.found_link = ''
        self.style_id = ''
        self.prod_id = ''
        self.form_key = ''

    def cook(self):
        self.log('Starting up')
        self.log('Attempting to scrape category {}'.format(self.settings['category']))
        if self.scrape_product():
            self.log('Attempting ATC')
            if self.add_to_cart():
                self.log('Attempting checkout')
                if self.checkout():
                    self.log('Checked out')
                else:
                    self.log('Failed to check out')
            else:
                self.log('Failed to ATC')
        else:
            self.log('Failed to scrape category')

    def log(self, text):
        current = datetime.now()
        print('== {} == {}'.format(colored(str(current), 'blue'), str(text)))

    def scrape_product(self):
        cat_url = 'http://supremenewyork.com/shop/all/{}'.format(self.settings['category'])
        url_arr = []
        name_arr = []
        style_arr = []

        self.log('Opening category page')
        r = self.session.request('GET', cat_url, verify=False)

        if r.status_code != 200:
            self.log('Encountered bad status code {}'.format(r.status_code))
            return False

        soup = BeautifulSoup(r.text, 'html.parser')

        for link in soup.select('a.name-link'):
            url = link.get('href')
            if url_arr.count(url) == 0:
                name_arr.append(link.get_text())
                url_arr.append(url)
            else:
                style_arr.append(link.get_text())

        self.log('Found {} products ( {} names / {} styles)'.format(str(len(url_arr)),
                                                                    str(len(name_arr)),
                                                                    str(len(style_arr))
                                                                    ))
        self.log(
            'Checking against keyword "{}" & style "{}"'.format(self.settings['name_key'], self.settings['style_key']))

        for i in range(0, len(url_arr)):
            if self.settings['name_key'] in name_arr[i].lower():
                if self.settings['style_key'] in style_arr[i].lower():
                    self.found_link = url_arr[i]
                    self.log('Found matching link {}'.format(self.found_link))
                    return True

        if not self.found_link:
            self.log('Did not find a matching link')
            return False

    def add_to_cart(self):
        url = 'http://supremenewyork.com/{}.json'.format(self.found_link)

        self.log("Opening product JSON")
        r = self.session.request('GET', url, verify=False)

        if r.status_code != 200:
            self.log('Encountered bad status {} opening product JSON'.format(r.status_code))
            return False

        j = r.json()

        self.log('Getting IDs')
        for e in j['styles']:
            if e['name'].lower() == self.settings['style_key']:
                self.style_id = e['id']
                self.log('Found style ID {}'.format(self.style_id))
                for s in e['sizes']:
                    if s['name'].lower() == self.settings['size_key']:
                        if s['stock_level'] == 1:
                            self.prod_id = s['id']
                            self.log('Found product ID {}'.format(self.prod_id))
                        if s['stock_level'] == 0:
                            self.log('Out of stock')
                            return False

        # The form key entry point seems to be not working at the moment

        # self.log('Looking for form key')
        # url = 'http://supremenewyork.com/{}'.format(self.found_link)
        # r = self.session.request("GET", url, verify=False)
        # if r.status_code != 200:
        #     self.log('Bad status code {} when looking for form key'.format(r.status_code))
        #     return False
        # soup = BeautifulSoup(r.text, 'html.parser')
        # sources = soup.findAll('form', {"action": True})
        # for s in sources:
        #     self.form_key = s['action']
        # self.log('Found form key {}'.format(self.form_key))
        # time.sleep(2)
        # url = 'http://www.supremenewyork.com/{}'.format(self.form_key)
        # p = "commit=add%20to%20cart&style={}&size={}&utf8=%E2%9C%93".format(self.style_id, self.prod_id)
        # r = self.session.request('POST', url, data=p, verify=False)
        # if r.status_code != 200:
        #     self.log('Bad status code {} when firing form POST'.format(r.status_code))
        #     return False

        self.session.get('http://www.supremenewyork.com/{}'.format(self.found_link))
        s = Select(self.session.find_element_by_xpath("//select[@id='size']"))
        s.select_by_value(str(self.prod_id))
        button = self.session.find_element_by_name("commit")
        button.click()

        time.sleep(1)
        self.log('Checking cart contents')
        r = self.session.request('GET', 'http://www.supremenewyork.com/shop/cart.json', verify=False)
        if str(self.prod_id) not in r.text:
            self.log('Product ID not in cart contents')
            return False

        return True

    def checkout(self):
        # This is a collection of the form elements. The selectors might change
        # so I try and adapt by using tab keys.

        self.session.get('https://www.supremenewyork.com/checkout')

        self.log('Finding form elements')
        name = self.session.find_element_by_id('order_billing_name')
        # email = self.session.find_element_by_id('order_email')
        tel = self.session.find_element_by_id('order_tel')
        # add = self.session.find_element_by_name('order[billing_address]')
        # ad2 = self.session.find_element_by_name('order[billing_address_2]')
        # zip = self.session.find_element_by_id('order_billing_zip')
        # city = self.session.find_element_by_id('order_billing_city')
        # state = Select(self.session.find_element_by_id('order_billing_state'))
        # country = Select(self.session.find_element_by_id('order_billing_country'))
        ctype = Select(self.session.find_element_by_id('credit_card_type'))
        # cc = self.session.find_element_by_name('order[cnb]')
        xm = Select(self.session.find_element_by_id('credit_card_month'))
        xy = Select(self.session.find_element_by_id('credit_card_year'))
        # cvv = self.session.find_element_by_xpath("//input[@size='4']")
        submit = self.session.find_element_by_xpath("//input[@type='submit']")

        self.log('Entering checkout details')
        name.send_keys(self.settings['f_name'] + ' ' + self.settings['l_name'], Keys.TAB,
                        self.settings['email'], Keys.TAB)
        tel.send_keys(self.settings['phone'], Keys.TAB,
                        self.settings['address'], Keys.TAB,
                        self.settings['address2'], Keys.TAB,
                        self.settings['zip'], Keys.TAB)
        ctype.select_by_visible_text(self.settings['type'])

        cardchain = ActionChains(self.session)
        cardchain.send_keys(Keys.TAB, self.settings['cc'])
        cardchain.perform()

        xm.select_by_value(self.settings['month'])
        xy.select_by_value(self.settings['year'])

        cvvchain = ActionChains(self.session)
        cvvchain.send_keys(Keys.TAB, self.settings['cvv'], Keys.TAB, Keys.SPACE)
        cvvchain.perform()

        # This is the delay you want to set to avoid ghost checkout

        time.sleep(self.settings['delay'])
        submit.click()

        return True


os = ObjSup()
os.cook()
