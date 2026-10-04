# Temporal Time Calculator

Computes the current time in **temporal (unequal) hours**.

Temporal hours divide daytime (sunrise → sunset) into 12 equal parts and
nighttime (sunset → sunrise) into a _separate_ 12 equal parts and is how most
people reckoned time before the advent of mechanical clocks and other devices
in the late middle ages. Because the length of daylight changes with the season,
a temporal hour is not fixed: in winter the daytime hours are shorter and the
nighttime hours longer (and vice versa). This differs from 24-hour "equinoctial"
time, so named after the equinox when temporal hours are equinoctial, which
splits the full day into 24 equal hours.

## Usage

Run with `--sunrise` and `--sunset` as `HH:MM` times:

````bash
python3 temporal_time.py --sunrise 06:00 --sunset 20:30 --now 14:00

`--now HH:MM` is optional; without it the program uses the system's current
wall-clock time.

### Reverse: temporal time -> wall clock

Convert a temporal instant back into equinoctial (24-hour) wall-clock time with
`--temporal-time`. It prints the wall-clock moment corresponding to that temporal
hour:

```bash
python3 temporal_time.py --sunrise 06:00 --sunset 20:30 --temporal-time 01:00
#   Input        : 01:00 (day block)
#   -> Equinoctial: 06:00   (i.e. sunrise)
````

Because the temporal time is 1-based (hour 1 starts at sunrise/sunset), use
`--period {day,night}` to disambiguate when a temporal time could belong to either
12-hour block (the default is `day`).

## Example

```
Temporal (unequal) hour calculator
  Sunrise : 06:00
  Sunset  : 20:30
  Day     : 14h 30m   1 temporal hour = 1h 12m (72.5 min)
  Night   : 9h 30m   1 temporal hour = 0h 48m (47.5 min)

  Current wall-clock time : 14:00
  You are in Daytime.
  Temporal time : 06:37  (6.62 of daytime, ~6.62 hours)
```

## How it works

1. **Day length** = sunset − sunrise (in minutes). Night length = 24h − day.
2. Each temporal hour = day length / 12 (daytime) or night length / 12 (night).
3. **Elapsed** within the current period = wall-clock time since sunrise (day)
   or sunset (night).
4. **Temporal time** = elapsed ÷ (temporal hour length).
