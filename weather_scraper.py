import asyncio
import logging
from dataclasses import dataclass, asdict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class WeatherData:
    location: str
    temperature: str
    condition: str
    humidity: str = "N/A"
    wind_speed: str = "N/A"
    barometer: str = "N/A"
    dewpoint: str = "N/A"
    visibility: str = "N/A"

class ProductionWeatherScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        
    async def start(self):
        """Initializes the browser session."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.firefox.launch(headless=self.headless)
        logging.info("Browser initialized.")

    async def fetch_weather(self, lat: str, lon: str) -> WeatherData | None:
        """Navigates to the page and extracts weather data robustly."""
        if not self.browser:
            raise RuntimeError("Browser not started. Call start() first.")

        url = f"https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}"
        
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/122.0"
        )
        page = await context.new_page()

        try:
            logging.info(f"Navigating to {url}")
            await page.goto(url, wait_until="networkidle", timeout=15000)

            location_text = await page.locator("h2.panel-title").first.inner_text(timeout=5000)
            temp_text = await page.locator(".myforecast-current-lrg").inner_text(timeout=5000)
            condition_text = await page.locator(".myforecast-current").first.inner_text()

            weather = WeatherData(
                location=location_text.strip(),
                temperature=temp_text.strip(),
                condition=condition_text.strip()
            )

            table_rows = await page.locator("div#current_conditions_detail table tr").all()
            
            for row in table_rows:
                label = await row.locator("td").nth(0).inner_text()
                value = await row.locator("td").nth(1).inner_text()
                
                label_clean = label.strip().lower()
                
                if "humidity" in label_clean:
                    weather.humidity = value.strip()
                elif "wind speed" in label_clean:
                    weather.wind_speed = value.strip()
                elif "barometer" in label_clean:
                    weather.barometer = value.strip()
                elif "dewpoint" in label_clean:
                    weather.dewpoint = value.strip()
                elif "visibility" in label_clean:
                    weather.visibility = value.strip()

            logging.info(f"Successfully scraped weather for: {weather.location}")
            return weather

        except PlaywrightTimeoutError:
            logging.error("Timeout: The page or elements took too long to load.")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return None
        finally:
            await context.close()

    async def close(self):
        """Cleans up browser resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logging.info("Browser closed. Resources freed.")

async def main():
    lat = "40.7143"
    lon = "-74.006"

    scraper = ProductionWeatherScraper(headless=True)
    
    try:
        await scraper.start()
        data = await scraper.fetch_weather(lat, lon)
        
        if data:
            print("\n" + "="*30)
            print(" WEATHER DATA COMPILED")
            print("="*30)
            # Convert the dataclass to a dictionary for easy printing/saving
            for key, value in asdict(data).items():
                # Formatting the keys nicely for the terminal
                print(f"{key.replace('_', ' ').title():<15}: {value}")
            print("="*30 + "\n")
            
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())