# 355CD / Region 5 Fleet Forecast 2027

Interactive dashboard that forecasts 2027 fleet costs for McCoy's Region 5 (355CD Pharr Central Delivery, 355 Pharr Reload and 11 stores) and compares the current delivery model with scenarios that reassign, terminate or relocate assets.

Open `index.html` in a browser (or the GitHub Pages site). Scenario changes are kept in the viewer's browser only.

**Saving and sharing a scenario:** use **Export to Excel** to download a workbook (Summary, Changes, Volume overrides, Assets, Monthly, Truck utilization, Forklift utilization, Inputs). Use **Import scenario** on the Reassign assets tab to load that workbook back; the changes, delivery overrides and inputs are restored. The Excel library loads from cdnjs, so exporting needs an internet connection.

## What it shows
- Baseline vs. scenario 2027 costs by month, location, asset and cost category.
- Two views: **location charges** (355CD/355: fuel, maintenance, depreciation, lease; stores: fuel, flat rate, $0.425 per truck mile) and **Region 5 operating cost** (what the company actually spends).
- Asset reassignment between locations, Terminate (sell / return lease) and Relocate out of Region 5, each with an effective month.
- Delivery-truck utilization (deliveries, miles, cost per delivery, time-away utilization) and forklift utilization (hours per day vs. the company average, yard tickets).
- Editable assumptions: 2027 fuel and propane rates, flat rates, mileage rate, mileage and maintenance trends, deliveries per moved truck.

## Files
- `index.html` — the built dashboard.
- `data/data.json` — asset-level model inputs and store metrics built from the source exports.
- `src/build_data.py` — builds `data.json` from the source exports (asset roster, depreciation, leases, maintenance, WEX fuel, propane, Geotab miles, store metrics, yard tickets). The source exports are not in this repo.
- `src/load_miles.py` — combines the monthly Geotab mileage files.
- `src/template.html` — dashboard source; `src/build_html.py` injects the data and logo to produce `index.html`.

Assumptions and method are documented on the dashboard's **Assumptions & data** tab.
