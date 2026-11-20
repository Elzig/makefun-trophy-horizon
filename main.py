"""Forecast trophy rates with robust log-odds trends and horizon uncertainty."""
import json
import math
import os
from pathlib import Path
from statistics import median


def logit(rate):
    p = min(.9999, max(.0001, rate / 100))
    return math.log(p / (1 - p))


def forecast(case):
    from datetime import datetime
    def stamp(value):
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    history = case['history']
    horizon = case['horizon_minutes'] / 60
    result = []
    for index, trophy in enumerate(case['trophies']):
        observations = []
        for row in history:
            rate = row['rates'][index]
            if rate is None:
                continue
            item = (stamp(row['at']) / 3600, logit(rate))
            if not observations or item[1] != observations[-1][1]:
                observations.append(item)
        if not observations:
            center, spread = -5, 2
        else:
            last_time, center = observations[-1]
            recent = observations[-7:]
            slopes = [(b[1]-a[1])/(b[0]-a[0])
                      for a, b in zip(recent, recent[1:])
                      if b[0] > a[0]]
            slope = median(slopes) if slopes else 0
            # Saturating extrapolation prevents launch-day changes growing forever.
            extension = 24 * math.log1p(horizon / 24)
            center += max(-.08, min(.08, slope)) * extension * .55
            spread = .18 + .50 * math.log1p(horizon / 12)
            if len(observations) < 3:
                spread += .45
            if trophy['tier'] == 'platinum':
                spread += .35
        quantiles = [round(100/(1+math.exp(-max(-25,min(25,center+z*spread)))),6)
                     for z in (-1.644854,-.67449,0,.67449,1.644854)]
        result.append({'id': trophy['id'], 'q': quantiles})
    return {'trophies': result}


if __name__ == '__main__':
    output = Path(os.environ.get('MAKEFUN_OUTPUT_DIR', '/output'))
    output.mkdir(parents=True, exist_ok=True)
    for source in sorted(Path(os.environ.get('MAKEFUN_INPUT_DIR', '/input')).glob('*.in')):
        case = json.loads(source.read_text(encoding='utf-8'))
        (output / (source.stem + '.out')).write_text(
            json.dumps(forecast(case), separators=(',', ':')), encoding='utf-8')
