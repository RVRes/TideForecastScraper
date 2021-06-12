from TideForecastScraper import TideForecastScraper
from tabulate import tabulate

if __name__ == '__main__':
    scraper = TideForecastScraper()
    result = scraper.get_all_daylights_low_tides
    for place, tides in result.items():
        print('', place, sep='\n')
        print(tabulate(tides, tablefmt="grid"))
