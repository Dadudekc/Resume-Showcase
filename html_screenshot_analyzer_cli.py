import os
import logging
import time
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.common.exceptions import WebDriverException, TimeoutException
from PIL import Image
import openai
from shutil import which

# -------------------------------------------------------------------
# Section 1: Argument Parsing for CLI and Default Interactive Input
# -------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="HTML Screenshot Analyzer with AI.")
    parser.add_argument("--driver_path", help="Path to the ChromeDriver executable (leave empty to auto-detect)", default=None)
    parser.add_argument("--html_dir", help="Directory where HTML files are stored", required=True)
    parser.add_argument("--output_dir", help="Directory to save outputs", required=True)
    parser.add_argument("--api_key", help="OpenAI API key", required=True)
    parser.add_argument("--browser", choices=["chrome", "firefox"], help="Browser to use for capturing screenshots", default="chrome")
    parser.add_argument("--use_ai", help="Enable AI-based explanations", action='store_true')
    return parser.parse_args()

# -------------------------------------------------------------------
# Section 2: Setup Functions (Driver, Logging, OpenAI)
# -------------------------------------------------------------------
def setup_driver(driver_path, browser="chrome"):
    """
    Initializes the Selenium WebDriver with headless browser options.
    Supports both Chrome and Firefox browsers.
    """
    if browser == "firefox":
        driver_service = FirefoxService(executable_path=driver_path or which("geckodriver"))
        driver = webdriver.Firefox(service=driver_service)
    else:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        driver_service = Service(executable_path=driver_path or which("chromedriver"))
        driver = webdriver.Chrome(service=driver_service, options=chrome_options)
    logging.info(f"WebDriver initialized with {browser}.")
    return driver

def setup_logging(output_dir):
    """
    Configures logging with a log file in the output directory.
    """
    log_file = os.path.join(output_dir, "process_log.log")
    logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def setup_openai(api_key):
    """
    Configures OpenAI with the provided API key.
    """
    openai.api_key = api_key

# -------------------------------------------------------------------
# Section 3: Core Functionalities (Screenshot, AI Processing, Saving)
# -------------------------------------------------------------------
def capture_screenshot(driver, html_file_path, output_image_path):
    """
    Captures a screenshot of an HTML file using the WebDriver.
    """
    try:
        driver.get(f"file:///{html_file_path}")
        time.sleep(2)
        driver.save_screenshot(output_image_path)
        logging.info(f"Screenshot captured: {output_image_path}")
        return output_image_path
    except (WebDriverException, TimeoutException) as e:
        logging.error(f"Error capturing screenshot for {html_file_path}: {str(e)}")
        return None

def process_image_with_openai(image_path):
    """
    Sends the screenshot to OpenAI's API to get an explanation of the content.
    """
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

    response = openai.Image.create(
        prompt="Describe the content of this screenshot in simple terms:",
        images=image_data,
        n=1,
        size="1024x1024"
    )
    explanation = response['choices'][0]['text']
    logging.info(f"Explanation generated for image: {image_path}")
    return explanation

def save_explanation_to_file(explanation, output_path):
    """
    Saves the AI-generated explanation to a text file.
    """
    with open(output_path, "w") as file:
        file.write(explanation)
    logging.info(f"Explanation saved: {output_path}")

# -------------------------------------------------------------------
# Section 4: Main Workflow for Processing HTML Files
# -------------------------------------------------------------------
def main():
    args = parse_args()
    
    # Setup logging and OpenAI
    setup_logging(args.output_dir)
    setup_openai(args.api_key)
    
    # Setup directories
    screenshots_dir = os.path.join(args.output_dir, "screenshots")
    explanations_dir = os.path.join(args.output_dir, "explanations")
    os.makedirs(screenshots_dir, exist_ok=True)
    os.makedirs(explanations_dir, exist_ok=True)

    # Setup WebDriver
    try:
        driver = setup_driver(args.driver_path, args.browser)
    except WebDriverException as e:
        print("Error initializing WebDriver.")
        return
    
    # Process each HTML file in the directory
    for filename in os.listdir(args.html_dir):
        if filename.endswith(".html"):
            html_file_path = os.path.join(args.html_dir, filename)
            screenshot_path = os.path.join(screenshots_dir, filename.replace(".html", ".png"))
            explanation_path = os.path.join(explanations_dir, filename.replace(".html", ".txt"))
            
            # Capture screenshot
            screenshot = capture_screenshot(driver, html_file_path, screenshot_path)
            
            # Process with OpenAI if enabled
            if screenshot and args.use_ai:
                explanation = process_image_with_openai(screenshot)
                if explanation:
                    save_explanation_to_file(explanation, explanation_path)
                    print(f"Explanation saved for {filename}")

    driver.quit()

# -------------------------------------------------------------------
# Example Usage (Main Section)
# -------------------------------------------------------------------
if __name__ == "__main__":
    main()
