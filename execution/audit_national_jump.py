"""
Audit: is the 2010 -> 2020 national MODIS step real, or a pipeline artifact?

Recomputes the SAME method used by execution/build_national_modis.py
(pixel-wise median of all 16-day MOD13Q1 composites in Apr 15 - May 31,
masked by 250m_16_days_pixel_reliability <= 1, threshold NDVI >= 0.40)
on small fixed test windows, for all four snapshot years.

Because every year is re-queried and recomputed identically here, a step that
survives this test cannot be caused by stale caches or mismatched methods in
the national build. It would then have to come from the source data itself.

Writes data/audit/national_jump_audit.json
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import re
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
import pystac_client
import planetary_computer

YEARS = [2000, 2010, 2020, 2025]
THRESHOLD = 0.40

# Fixed 1.5 x 1.5 degree windows with known ecological character.
WINDOWS = {
    "western_ghats_forest": [74.0, 13.5, 75.5, 15.0],
    "thar_desert": [70.5, 26.5, 72.0, 28.0],
    "indo_gangetic_cropland": [76.5, 29.0, 78.0, 30.5],
    "central_india_dry_deciduous": [78.0, 20.5, 79.5, 22.0],
    "northeast_humid": [92.0, 25.0, 93.5, 26.5],
}

OUT_RES = 0.002  # ~220 m, matches the native MODIS grid


def composite_window(client, bbox, year, band_key="250m_16_days_NDVI"):
    """Median-composite the Apr 15 - May 31 window over `bbox` exactly as the national build does."""
    search = client.search(
        collections=["modis-13Q1-061"],
        bbox=bbox,
        datetime=f"{year}-04-15/{year}-05-31",
    )
    items = list(search.item_collection())

    tile_items = {}
    for it in items:
        m = re.search(r"h\d+v\d+", it.id)
        if m:
            tile_items.setdefault(m.group(0), []).append(it)

    lon_min, lat_min, lon_max, lat_max = bbox
    width = int(round((lon_max - lon_min) / OUT_RES))
    height = int(round((lat_max - lat_min) / OUT_RES))
    dst_transform = from_bounds(lon_min, lat_min, lon_max, lat_max, width, height)

    merged = np.full((height, width), np.nan, dtype=np.float32)
    scenes_read = 0
    scenes_failed = 0
    window_dates = []

    for tid, it_list in sorted(tile_items.items()):
        stack = []
        src_transform = None
        src_crs = None
        for it in sorted(it_list, key=lambda x: x.datetime or x.id):
            ndvi_asset = it.assets.get(band_key)
            qa_asset = it.assets.get("250m_16_days_pixel_reliability")
            if not ndvi_asset:
                continue
            try:
                with rasterio.open(ndvi_asset.href) as src:
                    ov_shape = (src.height // 8, src.width // 8)
                    ndvi_raw = src.read(1, out_shape=ov_shape)
                    src_transform = src.transform * src.transform.scale(
                        src.width / ov_shape[1], src.height / ov_shape[0]
                    )
                    src_crs = src.crs

                valid_mask = (ndvi_raw > -2000) & (ndvi_raw <= 10000)
                if qa_asset:
                    try:
                        with rasterio.open(qa_asset.href) as qa_src:
                            qa_raw = qa_src.read(1, out_shape=ov_shape)
                            valid_mask = valid_mask & (qa_raw <= 1)
                    except Exception:
                        pass

                stack.append(
                    np.where(valid_mask, ndvi_raw.astype(np.float32) * 0.0001, np.nan)
                )
                scenes_read += 1
                if it.datetime:
                    window_dates.append(it.datetime.strftime("%Y-%m-%d"))
            except Exception:
                scenes_failed += 1

        if not stack:
            continue

        with np.errstate(all="ignore"):
            tile_ndvi = stack[0] if len(stack) == 1 else np.nanmedian(
                np.stack(stack, axis=0), axis=0
            )

        reprojected = np.full((height, width), np.nan, dtype=np.float32)
        reproject(
            source=tile_ndvi,
            destination=reprojected,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs="EPSG:4326",
            resampling=Resampling.bilinear,
            src_nodata=np.nan,
            dst_nodata=np.nan,
        )
        has_val = ~np.isnan(reprojected)
        merged[has_val] = reprojected[has_val]

    return {
        "ndvi": merged,
        "scene_count": scenes_read,
        "scene_failures": scenes_failed,
        "tile_count": len(tile_items),
        "composite_dates": sorted(set(window_dates)),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--window", help="Run a full 2000-2025 annual series for one window name")
    parser.add_argument("--out", default="data/audit/national_jump_audit.json")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    client = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    if args.window:
        bbox = WINDOWS[args.window]
        print(f"Annual series 2000-2025 for [{args.window}] {bbox}")
        series = {}
        for yr in range(2000, 2026):
            r = composite_window(client, bbox, yr)
            vals = r["ndvi"][~np.isnan(r["ndvi"])]
            if vals.size == 0:
                print(f"  {yr}: NO VALID PIXELS")
                series[str(yr)] = {"valid_pixels": 0}
                continue
            series[str(yr)] = {
                "valid_pixels": int(vals.size),
                "ndvi_median": round(float(np.median(vals)), 4),
                "green_fraction_pct": round(float((vals >= THRESHOLD).mean() * 100.0), 2),
                "scene_count": r["scene_count"],
                "tile_count": r["tile_count"],
            }
            print(
                f"  {yr}: green {series[str(yr)]['green_fraction_pct']:5.2f}%  "
                f"median NDVI {series[str(yr)]['ndvi_median']:.4f}  "
                f"({r['scene_count']} scenes)"
            )
        payload = {
            "title": f"Annual 2000-2025 series for {args.window}",
            "method": "median composite, reliability<=1, NDVI>=0.40",
            "window": args.window,
            "bbox": bbox,
            "series": series,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {out_path}")
        return

    results = {}
    for name, bbox in WINDOWS.items():
        print(f"\n[{name}]")
        results[name] = {"bbox": bbox, "years": {}}
        for yr in YEARS:
            r = composite_window(client, bbox, yr)
            vals = r["ndvi"][~np.isnan(r["ndvi"])]
            if vals.size == 0:
                print(f"  {yr}: NO VALID PIXELS ({r['scene_count']} scenes)")
                results[name]["years"][str(yr)] = {"valid_pixels": 0}
                continue
            entry = {
                "valid_pixels": int(vals.size),
                "ndvi_mean": round(float(np.mean(vals)), 4),
                "ndvi_median": round(float(np.median(vals)), 4),
                "ndvi_p10": round(float(np.percentile(vals, 10)), 4),
                "ndvi_p90": round(float(np.percentile(vals, 90)), 4),
                "green_fraction_pct": round(float((vals >= THRESHOLD).mean() * 100.0), 2),
                "scene_count": r["scene_count"],
                "scene_failures": r["scene_failures"],
                "tile_count": r["tile_count"],
                "composite_dates": r["composite_dates"],
            }
            results[name]["years"][str(yr)] = entry
            print(
                f"  {yr}: green {entry['green_fraction_pct']:5.2f}%  "
                f"median NDVI {entry['ndvi_median']:.4f}  "
                f"p10 {entry['ndvi_p10']:.3f}  p90 {entry['ndvi_p90']:.3f}  "
                f"({entry['scene_count']} scenes, {entry['tile_count']} tiles)"
            )

    payload = {
        "title": "National MODIS 2010 to 2020 step audit",
        "method": (
            "Same median-composite + reliability<=1 + NDVI>=0.40 method as "
            "execution/build_national_modis.py, re-queried per year per window"
        ),
        "threshold_ndvi": THRESHOLD,
        "years": YEARS,
        "windows": results,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    print("\nSummary: green fraction per window per year")
    header = f"{'window':30s}" + "".join(f"{y:>9d}" for y in YEARS) + f"{'2010->2020':>12s}"
    print(header)
    for name, res in results.items():
        row = f"{name:30s}"
        for yr in YEARS:
            e = res["years"].get(str(yr), {})
            row += f"{e.get('green_fraction_pct', float('nan')):9.2f}"
        a = res["years"].get("2010", {}).get("green_fraction_pct")
        b = res["years"].get("2020", {}).get("green_fraction_pct")
        row += f"{(b - a) if (a is not None and b is not None) else float('nan'):12.2f}"
        print(row)


if __name__ == "__main__":
    main()
