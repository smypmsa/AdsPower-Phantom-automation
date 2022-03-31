from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from support import functions as f
from support import ui_elements as ui

import glob
import os
import csv
import json
import requests
import time


# Load config parameters
with open('config.json') as config:
    CONFIG = json.load(config)

# Create url to get all profiles and send the request
list_url = '{}:{}/api/v1/user/list?page_size={}'.format(CONFIG['ADSPOWER_URL'],
                                                        CONFIG['ADSPOWER_PORT'],
                                                        CONFIG['PAGE_SIZE'],)
resp_list = requests.get(list_url).json()

# Get profiles which already done
list_of_files = os.listdir(CONFIG['FOLDER_FOR_KEYS'])
list_of_names = [filename.split('.')[0] for filename in list_of_files]

# Other variables
wallet_already_exists = True

# ---------------------------------------------------------------------------------------
# Start processing each profile
# ---------------------------------------------------------------------------------------

for profile in resp_list['data']['list']:

    # ---------------------------------------------------------------------------------------
    # Preparation
    # ---------------------------------------------------------------------------------------

    # Check if the profile has been processed before
    if profile['user_id'] in list_of_names:
        print('{} already processed'.format(profile['user_id']))
        continue

    # Create requests strings
    open_url = '{}:{}/api/v1/browser/start?user_id={}'.format(CONFIG['ADSPOWER_URL'],
                                                              CONFIG['ADSPOWER_PORT'],
                                                              profile['user_id'])

    close_url = '{}:{}/api/v1/browser/stop?user_id={}'.format(CONFIG['ADSPOWER_URL'],
                                                              CONFIG['ADSPOWER_PORT'],
                                                              profile['user_id'])

    # Open a profile in AdsPower
    resp = requests.get(open_url).json()
    # Save the current id (logs)
    CURRENT_RECORD = [profile['user_id']]

    # Set up selenium
    chrome_driver = resp["data"]["webdriver"]
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", resp["data"]["ws"]["selenium"])
    driver = webdriver.Chrome(chrome_driver, options=chrome_options)

# ---------------------------------------------------------------------------------------
# Set up Phantom
# ---------------------------------------------------------------------------------------

    # ---------------------------------------------------------------------------------------
    # Log in wallet (if a wallet already created)
    # (it throws exception if an element not found (wallet doesn't exist))
    # ---------------------------------------------------------------------------------------
    # Go to popup.html (Phantom)
    driver.get(CONFIG['PHANTOM_URL2'])
    # Close other tabs
    f.close_other_tabs(driver)
    # Try to create wallet
    driver.get(CONFIG['PHANTOM_URL2'])

    try:
        # Check if Unlock button exists
        flow_flag = f.check_element(driver, ui.xpath_unlock)
        if flow_flag:
            # Enter password
            f.sendkeys_element(driver, ui.xpath_loginpass, CONFIG['DEFAULT_PASS'])
            f.click_element(driver, ui.xpath_unlock)
            CURRENT_RECORD.append('Wallet already created')
    except Exception as err:
        print(err.args)
        time.sleep(CONFIG['GLOBAL_SLEEP'])
        wallet_already_exists = False
        pass

    # ---------------------------------------------------------------------------------------
    # Create wallet (try to create if previous step threw an exception)
    # ---------------------------------------------------------------------------------------

    if not wallet_already_exists:

        # Go to onboarding.html (Phantom)
        driver.get(CONFIG['PHANTOM_URL1'])
        # Close other tabs
        f.close_other_tabs(driver)
        # Try to create wallet
        driver.get(CONFIG['PHANTOM_URL1'])

        try:
            # Check if Create button exists
            flow_flag = f.check_element(driver, ui.xpath_create1)
            if flow_flag:

                # Click Create button
                f.click_element(driver, ui.xpath_create1)

                # Enter a new password
                f.sendkeys_element(driver, ui.xpath_newpass, CONFIG['DEFAULT_PASS'])

                # Enter a new password once again (confirm)
                f.sendkeys_element(driver, ui.xpath_confirmpass, CONFIG['DEFAULT_PASS'])

                # Click Agree
                f.click_element(driver, ui.xpath_agreeterms)

                # Click Continue
                f.click_element(driver, ui.xpath_continue)

                # Get seed phrase
                seed = f.read_element(driver, ui.xpath_seed)
                seed_file = open(CONFIG['FOLDER_FOR_KEYS'] + '/' + profile['user_id'] + '.txt', "w")
                n = seed_file.write(seed)
                seed_file.close()

                # Click "I saved my ... "
                f.click_element(driver, ui.xpath_isavedseed)

                # Click Continue
                f.click_element(driver, ui.xpath_continue)

                CURRENT_RECORD.append('New wallet created')

        except Exception as err:
            print(err.args)
            time.sleep(CONFIG['GLOBAL_SLEEP'])
            pass

# ---------------------------------------------------------------------------------------
# Actual work
# ---------------------------------------------------------------------------------------
# Save processed ID to the file
    with open(CONFIG['FILE_RESULTS'], 'a', newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CURRENT_RECORD)

    print('Iteration finished')

# ---------------------------------------------------------------------------------------
# Finish
# ---------------------------------------------------------------------------------------
# Done! Quit and go to the next one
    driver.quit()
    requests.get(close_url)
