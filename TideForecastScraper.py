import aiohttp
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup as bs


class TideForecastScraper:

    def __init__(self):
        self._PAGES = {
            'Half Moon Bay, California': 'https://www.tide-forecast.com/locations/Half-Moon-Bay-California/tides/latest',
            'Huntington Beach, California': 'https://www.tide-forecast.com/locations/Huntington-Beach/tides/latest',
            'Providence, Rhode Island': 'https://www.tide-forecast.com/locations/Providence-Rhode-Island/tides/latest',
            'Wrightsville Beach, North Carolina': 'https://www.tide-forecast.com/locations/Wrightsville-Beach-North-Carolina/tides/latest'
        }
        self._DATES_ARGS = ('th', {'class': 'tide-table__day'})  # date element search const
        self._TIDES_ARGS = ('td', {'class': 'tide-table__part--low'})  # tide element search const
        self._LOW_TIDE_TIME_ARGS = ('span', {'class': 'tide-table__value-low'})  # low tide time element search const
        self._LOW_TIDE_HEIGHT_ARGS = ('span', {'class': 'tide-table__height'})  # low tide height element search const
        self._LOW_TIDE_UNIT_ARGS = ('span', {'class': 'tide-table__units'})  # low tide unit element search const
        self._SUN_SEARCH_ARGS = (
            'td', {'class': 'tide-table__part tide-table__part--sun tide-table__part--last'})  # sun element search const

    @staticmethod
    async def fetch(session, url):
        async with session.get(url[1]) as response:
            if response.status != 200:
                response.raise_for_status()
            return url[0], await response.text()

    @staticmethod
    async def fetch_all(session, urls):
        tasks = []
        for url in urls.items():
            task = asyncio.create_task(TideForecastScraper.fetch(session, url))
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        return results

    @staticmethod
    async def start_session(urls):
        async with aiohttp.ClientSession() as session:
            htmls = await TideForecastScraper.fetch_all(session, urls)
            return htmls

    def _get_low_tides(self, html: str):
        """
        Returns zip object with Tide data extraction from given HTML.
        :param html: HTML doc to parse.
        :return: ZIP (date:str, tide_time: list[str], tide_height: list[str], tide_height_units: list[str],
                                                                        sun:dict{sunrise:str , sunset:str})
        """
        soup = bs(html, 'html.parser')
        # Date
        el_dates = soup.findAll(*self._DATES_ARGS)
        lt_dates = [item['data-date'] for item in el_dates if 'data-date' in item.attrs]
        # Tides
        el_tides = soup.findAll(*self._TIDES_ARGS)
        lt_times = [list(map(bs.get_text, item.findAll(*self._LOW_TIDE_TIME_ARGS))) for item in el_tides]
        lt_heights = [list(map(bs.get_text, item.findAll(*self._LOW_TIDE_HEIGHT_ARGS))) for item in el_tides]
        lt_units = [list(map(bs.get_text, item.findAll(*self._LOW_TIDE_UNIT_ARGS))) for item in el_tides]
        # Sun_info
        el_sun = soup.findAll(*self._SUN_SEARCH_ARGS)
        lt_sun = [{'sunrise': item.next.get_text(), 'sunset': item.next.next_sibling.get_text()} for item in el_sun]
        if len(el_sun) != len(el_tides) != len(el_dates):
            raise Exception('Parsing error. Results arrays have different length')
        return list(zip(lt_dates, lt_times, lt_heights, lt_units, lt_sun))

    @staticmethod
    def _time_filer(lt_data: zip):
        """
        Return filtered result with tides from sunrise up to sunset.
        :param lt_data:
        :return: list[dict:{date, time, height, unit}]
        """
        def time_conv(ts):
            if ts[:2:] == '00':
                ts = '12' + ts[2::]
            return datetime.strptime(ts.strip(), '%I:%M%p')
        result = []
        for date, lt_times, lt_heights, lt_units, sun in lt_data:
            sunrise = time_conv(sun['sunrise']) if sun['sunrise'] else None
            sunset = time_conv(sun['sunset']) if sun['sunset'] else None
            if sunset is None or sunrise is None:
                continue
            for ind, lt_time in enumerate(lt_times):
                if sunrise <= time_conv(lt_time) <= sunset:
                    result.append({'date': date, 'time': lt_time, 'height': lt_heights[ind], 'unit': lt_units[ind]})
        return result

    @property
    def get_all_daylights_low_tides(self):
        """
        Public property to get daylight tides from different lincs using async calls.
        :return: dict{place, list[dict:{date, time, height, unit}]}
        """
        pages = asyncio.get_event_loop().run_until_complete(
            TideForecastScraper.start_session(self._PAGES))
        result = {}
        for page in pages:
            place = page[0]
            lt_raw_data = self._get_low_tides(page[1])
            result[place] = self._time_filer(lt_raw_data)
        return result
