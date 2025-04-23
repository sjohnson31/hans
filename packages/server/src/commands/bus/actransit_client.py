from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx


@dataclass
class BusArrival:
    line_name: str
    estimated_arrival_at: datetime
    estimation_made_at: datetime


def parse_actransit_time(time_str: str) -> datetime:
    return datetime.strptime('%Y%m%d %H:%M')


class ACTransitClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def bus_arrivals(self, stop_id: str, routes: list[str]) -> BusArrival:
        resp = httpx.get(
            urljoin(self.base_url, 'actrealtime/prediction'),
            params={
                'stpid': stop_id,
                'rt': ','.join(routes),
                'tmres': 'sec',
                'token': self.api_key,
            },
        )
        raw_arrivals = resp.json['bustime-response']['prd']
        arrivals = []
        for raw_arrival in raw_arrivals:
            arrivals += BusArrival(
                line_name=raw_arrival['rt'],
                estimation_made_at=parse_actransit_time(raw_arrival['tmstmp']),
                estimated_arrival_at=parse_actransit_time(raw_arrival['prdtm']),
            )

        return arrivals
