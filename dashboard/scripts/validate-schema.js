// Schema validator for data files consumed by the dashboard frontend
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDir = path.resolve(__dirname, "../public/data");

console.log("Checking data schemas...");

// 1. Validate loss_hotspots.json
const hotspotsPath = path.join(dataDir, "loss_hotspots.json");
if (!fs.existsSync(hotspotsPath)) {
  console.error("FAIL: Missing loss_hotspots.json at", hotspotsPath);
  process.exit(1);
}

const hotspotsData = JSON.parse(fs.readFileSync(hotspotsPath, "utf-8"));
const list = Array.isArray(hotspotsData)
  ? hotspotsData
  : hotspotsData.hotspots || [];

if (!list || list.length === 0) {
  console.error("FAIL: loss_hotspots.json has empty or invalid hotspots array");
  process.exit(1);
}

const requiredFields = ["rank", "zone_id", "zone_label", "net_change_pp"];
list.forEach((item, idx) => {
  requiredFields.forEach((field) => {
    if (item[field] === undefined || item[field] === null) {
      console.error(
        `FAIL: Hotspot index ${idx} missing required field '${field}':`,
        item
      );
      process.exit(1);
    }
  });
  if (typeof item.net_change_pp !== "number") {
    console.error(
      `FAIL: Hotspot index ${idx} field 'net_change_pp' must be a number, got:`,
      typeof item.net_change_pp
    );
    process.exit(1);
  }
});

console.log(`PASS: Verified ${list.length} hotspots in loss_hotspots.json.`);
