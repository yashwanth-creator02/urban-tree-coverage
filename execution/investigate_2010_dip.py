"""
Server-side batched investigation of the 2010 green cover dip in Bengaluru.
Evaluates the full annual series 2000-2025 in a single parallel GEE evaluation.
"""

import json
import ee
import numpy as np
from pathlib import Path

# Setup GEE connection
key_path = r"C:\Users\yashw\.config\gcp\ee-key.json"
with open(key_path, "r", encoding="utf-8") as f:
    key_info = json.load(f)

creds = ee.ServiceAccountCredentials(key_info["client_email"], key_data=json.dumps(key_info))
ee.Initialize(creds)
print("GEE initialized for batched 2010 dip investigation.")

roi = ee.Geometry.BBox(77.46, 12.83, 77.78, 13.14)

# Create a server-side list of years: 2000 to 2025
years_list = ee.List.sequence(2000, 2025)

def prep_landsat_image(img):
    qa = img.select("QA_PIXEL")
    clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
    
    # Check if bands are SR_B3/4 (L5/7) or SR_B4/5 (L8/9)
    bands = img.bandNames()
    is_l89 = bands.contains("SR_B5")
    
    # We can handle dynamically:
    # If L8/9:
    red = ee.Algorithms.If(is_l89, img.select("SR_B4").multiply(0.0000275).add(-0.2).multiply(0.9785).add(-0.0014),
                                  img.select("SR_B3").multiply(0.0000275).add(-0.2))
    nir = ee.Algorithms.If(is_l89, img.select("SR_B5").multiply(0.0000275).add(-0.2).multiply(0.9549).add(0.0062),
                                  img.select("SR_B4").multiply(0.0000275).add(-0.2))
    red_img = ee.Image(red)
    nir_img = ee.Image(nir)
    ndvi = nir_img.subtract(red_img).divide(nir_img.add(red_img)).rename("NDVI")
    return ndvi.updateMask(clear)

def get_year_data(year_num):
    yr = ee.Number(year_num)
    y_int = yr.toInt()
    
    # Jan 1 to Mar 31 of year
    start_date = ee.Date.fromYMD(y_int, 1, 1)
    end_date = ee.Date.fromYMD(y_int, 3, 31)
    
    # Rainfall: Oct 1 of previous year to Mar 31 of current year
    rain_start = ee.Date.fromYMD(y_int.subtract(1), 10, 1)
    rain_col = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterBounds(roi).filterDate(rain_start, end_date)
    rain_sum = rain_col.select("precipitation").sum()
    rain_val = rain_sum.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=5000,
        maxPixels=1e7
    ).get("precipitation")
    
    # Landsat collections
    l5 = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").filterBounds(roi).filterDate(start_date, end_date)
    l7 = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").filterBounds(roi).filterDate(start_date, end_date)
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(roi).filterDate(start_date, end_date)
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(roi).filterDate(start_date, end_date)
    
    l5_cnt = l5.size()
    l7_cnt = l7.size()
    l8_cnt = l8.size()
    l9_cnt = l9.size()
    
    # Merge all valid Landsat scenes for the dry season
    merged = l5.merge(l7).merge(l8).merge(l9)
    total_cnt = merged.size()
    
    # Process
    processed = merged.map(prep_landsat_image)
    median_ndvi = processed.median()
    
    stats = median_ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=120,
        maxPixels=1e8
    )
    ndvi_val = stats.get("NDVI")
    
    # Same-sensor-family L5 only (if available)
    l5_processed = l5.map(prep_landsat_image)
    l5_val = ee.Algorithms.If(l5_cnt.gt(0),
        l5_processed.median().reduceRegion(reducer=ee.Reducer.mean(), geometry=roi, scale=120, maxPixels=1e8).get("NDVI"),
        None)
        
    # Same-sensor-family L7 only (if available)
    l7_processed = l7.map(prep_landsat_image)
    l7_val = ee.Algorithms.If(l7_cnt.gt(0),
        l7_processed.median().reduceRegion(reducer=ee.Reducer.mean(), geometry=roi, scale=120, maxPixels=1e8).get("NDVI"),
        None)
        
    return ee.Feature(None, {
        "year": y_int,
        "mean_ndvi": ndvi_val,
        "l5_ndvi": l5_val,
        "l7_ndvi": l7_val,
        "l5_count": l5_cnt,
        "l7_count": l7_cnt,
        "l8_count": l8_cnt,
        "l9_count": l9_cnt,
        "total_count": total_cnt,
        "rainfall_oct_mar_mm": rain_val
    })

fc = ee.FeatureCollection(years_list.map(get_year_data))
print("Sending single batched evaluation to Earth Engine...")
records = fc.getInfo()["features"]

results = [f["properties"] for f in records]

print("\nYear | Total Scenes | L5 Scenes (NDVI) | L7 Scenes (NDVI) | L8/9 Scenes | Mean NDVI | Oct-Mar Rain (mm)")
print("-" * 95)
for r in results:
    y = r["year"]
    tot = r["total_count"]
    l5c = r["l5_count"]
    l5v = f"{r['l5_ndvi']:.3f}" if r["l5_ndvi"] is not None else "n/a"
    l7c = r["l7_count"]
    l7v = f"{r['l7_ndvi']:.3f}" if r["l7_ndvi"] is not None else "n/a"
    l89c = r["l8_count"] + r["l9_count"]
    ndvi = f"{r['mean_ndvi']:.3f}" if r["mean_ndvi"] is not None else "n/a"
    rain = f"{r['rainfall_oct_mar_mm']:.1f}" if r["rainfall_oct_mar_mm"] is not None else "n/a"
    print(f"{y} | {tot:2d} scenes   | L5: {l5c:2d} ({l5v:>5s})  | L7: {l7c:2d} ({l7v:>5s})  | L8/9: {l89c:2d}     | {ndvi:>9s} | {rain:>7s} mm")

# Compute 3-year running median
print("\n--- 3-Year Window Analysis ---")
for i in range(len(results)):
    r = results[i]
    y = r["year"]
    # Window of 3: i-1, i, i+1
    win_indices = [max(0, i-1), i, min(len(results)-1, i+1)]
    win_ndvis = [results[idx]["mean_ndvi"] for idx in win_indices if results[idx]["mean_ndvi"] is not None]
    r["median_3yr_ndvi"] = round(float(np.median(win_ndvis)), 4) if win_ndvis else None

out_path = Path("docs/investigation_2010_dip.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"\nSaved empirical results to {out_path}")
