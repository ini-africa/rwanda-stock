from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import datetime
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RSE_URL = "https://www.rse.rw/"

def get_driver():
    ua = UserAgent()
    user_agent = ua.random

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Stealth mode: remove webdriver property
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    return driver

def scrape_rse_data():
    """
    Scrapes RSE data using Selenium.
    """
    db = SessionLocal()
    driver = None
    try:
        logger.info("Starting RSE scrape...")
        driver = get_driver()
        driver.get(RSE_URL)
        
        # Wait for the table to load
        wait = WebDriverWait(driver, 20)
        # --- TAB 1: Equities ---
        logger.info("Scraping Equities (Tab 1)...")
        rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div#tab-1 table tbody tr")))
        
        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 4:
                    continue
                    
                symbol = cols[0].text.strip()
                price_text = cols[1].text.strip().replace(',', '')
                change_text = cols[3].text.strip().replace('%', '').replace('+', '')
                
                # Try to get Volume, High, Low if available (assuming standard indices, adjust if needed)
                # This is a guess based on typical layouts; if indices are wrong, it will default to 0/None
                volume = 0
                high = None
                low = None
                
                if len(cols) >= 5:
                    try:
                        volume = int(cols[4].text.strip().replace(',', ''))
                    except:
                        pass
                if len(cols) >= 7:
                     try:
                        high = float(cols[5].text.strip().replace(',', ''))
                        low = float(cols[6].text.strip().replace(',', ''))
                     except:
                        pass

                if not symbol or not price_text:
                    continue
                    
                try:
                    price = float(price_text)
                    change = float(change_text) if change_text and change_text != '-' else 0.0
                except ValueError:
                    continue
                
                stock = db.query(models.Stock).filter(models.Stock.symbol == symbol).first()
                if not stock:
                    stock = models.Stock(
                        symbol=symbol,
                        name=symbol,
                        current_price=price,
                        change=change,
                        volume=volume,
                        high=high,
                        low=low
                    )
                    db.add(stock)
                else:
                    stock.current_price = price
                    stock.change = change
                    stock.volume = volume
                    stock.high = high
                    stock.low = low
                    stock.updated_at = datetime.datetime.utcnow()
                
                # History
                history = models.PriceHistory(
                    stock_id=stock.id,
                    price=price,
                    timestamp=datetime.datetime.utcnow()
                )
                db.add(history)
                
            except Exception as e:
                logger.error(f"Error processing equity row: {e}")
                continue

        # --- TAB 2: Market Stats ---
        logger.info("Scraping Market Stats (Tab 2)...")
        try:
            # Click Tab 2
            tab2_link = driver.find_element(By.CSS_SELECTOR, "a[href='#tab-2']")
            driver.execute_script("arguments[0].click();", tab2_link)
            time.sleep(2) # Wait for tab switch
            
            stats_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div#tab-2 table tbody tr")))
            for row in stats_rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 2:
                    continue
                key = cols[0].text.strip()
                value = cols[1].text.strip()
                
                stat = db.query(models.MarketStat).filter(models.MarketStat.key == key).first()
                if not stat:
                    stat = models.MarketStat(key=key, value=value)
                    db.add(stat)
                else:
                    stat.value = value
                    stat.updated_at = datetime.datetime.utcnow()
        except Exception as e:
            logger.error(f"Error scraping Market Stats: {e}")

        # --- TAB 5: Bonds ---
        logger.info("Scraping Bonds (Tab 5)...")
        try:
            # Click Tab 5
            tab5_link = driver.find_element(By.CSS_SELECTOR, "a[href='#tab-5']")
            driver.execute_script("arguments[0].click();", tab5_link)
            
            # Wait for the table to be visible
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div#tab-5 table")))
            
            bond_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div#tab-5 table tbody tr")))
            logger.info(f"Found {len(bond_rows)} bond rows.")

            for row in bond_rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                col_texts = [c.text.strip() for c in cols]
                
                # We expect at least 6 columns based on debug:
                # 0: ID, 1: Security, 2: Issue Date, 3: Maturity, 4: Coupon, 5: Yield
                if len(cols) < 6:
                    continue
                
                security = col_texts[1]
                maturity = col_texts[3]
                coupon = col_texts[4]
                yield_txt = col_texts[5].replace('%', '')
                
                # Price is not explicitly in this table, defaulting to 0 or we could try to find it elsewhere
                price = 0.0 

                try:
                    yield_val = float(yield_txt) if yield_txt and yield_txt != '-' else 0.0
                except ValueError:
                    logger.warning(f"Could not parse bond yield for {security}: {yield_txt}")
                    yield_val = 0.0
                
                bond = db.query(models.Bond).filter(models.Bond.security == security).first()
                if not bond:
                    bond = models.Bond(
                        security=security,
                        coupon=coupon,
                        maturity=maturity,
                        price=price,
                        yield_percentage=yield_val
                    )
                    db.add(bond)
                else:
                    bond.coupon = coupon
                    bond.maturity = maturity
                    bond.yield_percentage = yield_val
                    bond.updated_at = datetime.datetime.utcnow()
        except Exception as e:
            logger.error(f"Error scraping Bonds: {e}")

        db.commit()
        logger.info("Scrape completed successfully.")
        
    except Exception as e:
        import traceback
        logger.error(f"Scraping failed: {e}")
        logger.error(traceback.format_exc())
        if driver:
            with open("debug.html", "w") as f:
                f.write(driver.page_source)
            logger.info("Saved debug.html")
    finally:
        if driver:
            driver.quit()
        db.close()

if __name__ == "__main__":
    scrape_rse_data()
