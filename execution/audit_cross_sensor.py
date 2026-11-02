"""
Cross-sensor comparability and threshold sensitivity audit.
Compares Landsat 7 (ETM+) vs Landsat 8 (OLI) over the coincident 2020 dry season (Jan-Mar)
in Bengaluru, applies Roy et al. (2016) harmonization, and evaluates threshold sensitivity
across NDVI 0.30, 0.35, 0.40, 0.45, 0.50.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import pystac_client
import planetary_computer as pc

from src.core.calibration import scale_surface_reflectance
from src.core.cloud_mask import is_clear_pixel
from src.core.indices import calculate_ndvi


def fetch_sensor_composite(platform: str, year: int = 2020, bbox: list = None, max_items: int = 3):
    if bbox is None:
        bbox = [77.46, 12.83, 77.75, 13.14]

    stac_client = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )
    search = stac_client.search(
        collections=["landsat-c2-l2"],
        bbox=bbox,
        datetime=f"{year}-01-01/{year}-03-31",
        query={"platform": {"eq": platform}, "eo:cloud_cover": {"lt": 20}},
        max_items=max_items,
    )
    items = list(search.items())
    print(f"[{platform}] Retrieved {len(items)} scenes for {year} Jan-Mar.")

    # Band mappings
    if platform == "landsat-7":
        red_key = "red"  # B3
        nir_key = "nir08"  # B4
    else:  # landsat-8
        red_key = "red"  # B4
        nir_key = "nir08"  # B5

    red_arrays = []
    nir_arrays = []
    valid_masks = []
    ref_meta = None

    for idx, item in enumerate(items[:max_items]):
        red_href = item.assets[red_key].href
        nir_href = item.assets[nir_key].href
        qa_href = item.assets["qa_pixel"].href

        with rasterio.open(red_href) as src_r:
            proj_bounds = transform_bounds("EPSG:4326", src_r.crs, *bbox)
            win = from_bounds(*proj_bounds, transform=src_r.transform)
            win = win.round_offsets().round_lengths()
            red_dn = src_r.read(1, window=win)
            if ref_meta is None:
                ref_meta = {
                    "transform": src_r.window_transform(win),
                    "shape": red_dn.shape,
                    "crs": src_r.crs,
                }

        with rasterio.open(nir_href) as src_n:
            nir_dn = src_n.read(1, window=win)

        with rasterio.open(qa_href) as src_qa:
            qa_dn = src_qa.read(1, window=win)

        # Cloud mask & reflectance
        is_clear = is_clear_pixel(qa_dn)
        is_valid = is_clear & (red_dn > 0) & (nir_dn > 0)

        red_sr = scale_surface_reflectance(red_dn)
        nir_sr = scale_surface_reflectance(nir_dn)

        red_sr[~is_valid] = np.nan
        nir_sr[~is_valid] = np.nan

        red_arrays.append(red_sr)
        nir_arrays.append(nir_sr)
        valid_masks.append(is_valid)

    # Median composite
    red_stack = np.stack(red_arrays, axis=0)
    nir_stack = np.stack(nir_arrays, axis=0)

    med_red = np.nanmedian(red_stack, axis=0)
    med_nir = np.nanmedian(nir_stack, axis=0)

    comp_valid = (~np.isnan(med_red)) & (~np.isnan(med_nir))
    ndvi = np.full(med_red.shape, np.nan, dtype=np.float32)
    ndvi[comp_valid] = calculate_ndvi(med_nir[comp_valid], med_red[comp_valid])

    return {
        "platform": platform,
        "red": med_red,
        "nir": med_nir,
        "ndvi": ndvi,
        "valid": comp_valid,
    }


def run_audit():
    cache_file = Path("data/cache/sensor_audit_2020.npz")
    if cache_file.exists():
        print(f"Loading cached audit arrays from {cache_file}...")
        data = np.load(cache_file)
        l7_ndvi = data["l7_ndvi"]
        l7_valid = data["l7_valid"]
        l8_ndvi = data["l8_ndvi"]
        l8_valid = data["l8_valid"]
        l8_red = data["l8_red"]
        l8_nir = data["l8_nir"]
    else:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        print("Fetching Landsat 7 (ETM+) composite for 2020...")
        l7 = fetch_sensor_composite("landsat-7", year=2020)
        print("Fetching Landsat 8 (OLI) composite for 2020...")
        l8 = fetch_sensor_composite("landsat-8", year=2020)

        l7_ndvi = l7["ndvi"]
        l7_valid = l7["valid"]
        l8_ndvi = l8["ndvi"]
        l8_valid = l8["valid"]
        l8_red = l8["red"]
        l8_nir = l8["nir"]

        np.savez_compressed(
            cache_file,
            l7_ndvi=l7_ndvi,
            l7_valid=l7_valid,
            l8_ndvi=l8_ndvi,
            l8_valid=l8_valid,
            l8_red=l8_red,
            l8_nir=l8_nir,
        )

    # Coincident valid pixels
    common_valid = l7_valid & l8_valid
    n_common = int(np.count_nonzero(common_valid))
    print(f"\nCommon valid pixels between Landsat 7 & Landsat 8 in 2020: {n_common:,}")

    v_l7 = l7_ndvi[common_valid]
    v_l8 = l8_ndvi[common_valid]

    # Roy et al. (2016) Harmonization:
    # Converting OLI surface reflectance to ETM+ equivalent
    # Red_etm = 0.0006 + 0.9328 * Red_oli
    # NIR_etm = 0.0436 + 0.8339 * NIR_oli
    l8_red_common = l8_red[common_valid]
    l8_nir_common = l8_nir[common_valid]
    harm_red = 0.0006 + 0.9328 * l8_red_common
    harm_nir = 0.0436 + 0.8339 * l8_nir_common
    v_l8_harm = (harm_nir - harm_red) / (harm_nir + harm_red)

    mean_diff_raw = float(np.mean(v_l8 - v_l7))
    mean_diff_harm = float(np.mean(v_l8_harm - v_l7))
    corr_raw = float(np.corrcoef(v_l7, v_l8)[0, 1])
    corr_harm = float(np.corrcoef(v_l7, v_l8_harm)[0, 1])

    print(f"\nMean NDVI (L7 ETM+): {np.mean(v_l7):.4f}")
    print(f"Mean NDVI (L8 OLI Raw): {np.mean(v_l8):.4f} (Mean Bias: {mean_diff_raw:+.4f})")
    print(f"Mean NDVI (L8 Harmonized Roy 2016): {np.mean(v_l8_harm):.4f} (Mean Bias: {mean_diff_harm:+.4f})")
    print(f"Correlation (Raw): {corr_raw:.4f}")
    print(f"Correlation (Harmonized): {corr_harm:.4f}")

    thresholds = [0.30, 0.35, 0.40, 0.45, 0.50]
    results_table = []

    print("\n--- Threshold Sensitivity Comparison (Coincident Pixels) ---")
    print(f"{'Threshold':<10} | {'L7 Green %':<12} | {'L8 Raw %':<12} | {'L8 Harm %':<12} | {'Raw Diff (pp)':<14} | {'Harm Diff (pp)':<14}")
    print("-" * 85)

    for th in thresholds:
        pct_l7 = float(np.count_nonzero(v_l7 >= th) / n_common * 100.0)
        pct_l8 = float(np.count_nonzero(v_l8 >= th) / n_common * 100.0)
        pct_l8_harm = float(np.count_nonzero(v_l8_harm >= th) / n_common * 100.0)
        raw_diff_pp = pct_l8 - pct_l7
        harm_diff_pp = pct_l8_harm - pct_l7

        row = {
            "threshold": th,
            "l7_pct": round(pct_l7, 2),
            "l8_raw_pct": round(pct_l8, 2),
            "l8_harm_pct": round(pct_l8_harm, 2),
            "raw_diff_pp": round(raw_diff_pp, 2),
            "harm_diff_pp": round(harm_diff_pp, 2),
        }
        results_table.append(row)
        print(f"{th:<10.2f} | {pct_l7:<12.2f} | {pct_l8:<12.2f} | {pct_l8_harm:<12.2f} | {raw_diff_pp:<+14.2f} | {harm_diff_pp:<+14.2f}")

    # Multi-year historical threshold sensitivity using our cached composites
    print("\n--- Multi-Year Threshold Sensitivity (2000, 2010, 2020, 2025) ---")
    years = [2000, 2010, 2020, 2025]
    multi_year_sensitivity = {}
    for yr in years:
        comp_path = Path(f"data/cache/composite_{yr}.npz")
        if comp_path.exists():
            c = np.load(comp_path)
            nd = calculate_ndvi(c["nir"], c["red"])
            val = (~np.isnan(nd)) & (~np.isnan(c["red"])) & (~np.isnan(c["nir"]))
            v_nd = nd[val]
            n_tot = len(v_nd)
            multi_year_sensitivity[yr] = {
                f"th_{th:.2f}": round(float(np.count_nonzero(v_nd >= th) / n_tot * 100.0), 2)
                for th in thresholds
            }
            print(f"Year {yr}: {multi_year_sensitivity[yr]}")

    audit_summary = {
        "coincident_pixels": n_common,
        "mean_l7_ndvi": round(float(np.mean(v_l7)), 4),
        "mean_l8_raw_ndvi": round(float(np.mean(v_l8)), 4),
        "mean_l8_harm_ndvi": round(float(np.mean(v_l8_harm)), 4),
        "raw_bias": round(mean_diff_raw, 4),
        "harm_bias": round(mean_diff_harm, 4),
        "correlation": round(corr_raw, 4),
        "threshold_comparison": results_table,
        "multi_year_sensitivity": multi_year_sensitivity,
    }

    out_file = Path("docs/sensor_audit_report.json")
    with open(out_file, "w") as f:
        json.dump(audit_summary, f, indent=2)
    print(f"\nAudit complete. Saved summary to {out_file}")


if __name__ == "__main__":
    run_audit()
