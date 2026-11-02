import geopandas as gpd

gdf_states = gpd.read_file("dashboard/public/data/india_states.geojson")
gdf_dist = gpd.read_file("dashboard/public/data/india_districts.geojson")

print("--- STATE SANITY CHECKS (2025 Real MODIS High Perennial Veg %) ---")
for sname in ["Kerala", "Goa", "Mizoram", "Arunachal Pradesh", "Rajasthan", "Punjab", "Delhi"]:
    m = gdf_states[gdf_states["name"] == sname]
    if len(m) > 0:
        row = m.iloc[0]
        val = row.get("green_pct_2025")
        print(f"  {sname:<22}: {val} %")

print("\n--- DISTRICT SANITY CHECKS (2025 Real MODIS High Perennial Veg %) ---")
for dname in ["Jaisalmer", "Bikaner", "Wayanad", "South Goa", "Central Delhi", "Bangalore", "Aizawl"]:
    m = gdf_dist[gdf_dist["name"].str.contains(dname, case=False, na=False)]
    for _, row in m.iterrows():
        lbl = f"{row['name']} ({row.get('state_name', '')})"
        val = row.get("green_pct_2025")
        print(f"  {lbl:<38}: {val} %")
