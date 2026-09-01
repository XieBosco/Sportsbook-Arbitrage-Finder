import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
import dataclasses

# Add needed paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from arbfinder.parsers.betano import BetanoParser
from arbfinder.parsers.betmgm import BetMGMParser
from arbfinder.parsers.caesars import CaesarsParser
from arbfinder.parsers.draftkings import DraftKingsParser
from arbfinder.parsers.fanduel import FanDuelParser

from arbfinder.normalization.normalizer import Normalizer
from arbfinder.normalization.book_normalizers.betano_normalizer import BetanoNormalizer
from arbfinder.normalization.book_normalizers.betmgm_normalizer import BetMGMNormalizer
from arbfinder.normalization.book_normalizers.caesars_normalizer import CaesarsNormalizer
from arbfinder.normalization.book_normalizers.draftkings_normalizer import DraftKingsNormalizer
from arbfinder.normalization.book_normalizers.fanduel_normalizer import FanDuelNormalizer

from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.matching.output import MatchOutputBuilder

from arbfinder.scanner.market_grouper import MarketGrouper
from arbfinder.scanner.staleness_filter import StalenessFilter
from arbfinder.scanner.dedup_tracker import DedupTracker
from arbfinder.scanner.sinks.base_sink import OpportunitySink
from arbfinder.scanner.threshold_config import ScannerThresholds
from arbfinder.scanner.scanner import Scanner

from arbfinder.scanner.market_grouper import MarketGroupKey

def decimal_to_american(decimal_odds: float) -> str:
    if decimal_odds >= 2.0:
        american = (decimal_odds - 1.0) * 100.0
        return f"+{round(american)}"
    else:
        american = -100.0 / (decimal_odds - 1.0)
        return str(round(american))

def write_arb_summary(filepath, arb_info, duration, reason):
    opp = arb_info["opp"]
    with open(filepath, "a") as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"OPPORTUNITY DETECTED! Margin: {opp.margin:.2%}\n")
        f.write(f"Match: {opp.away_team} @ {opp.home_team} | {opp.market_type} | Line: {opp.line}\n")
        f.write(f"Duration: {duration:.1f} seconds (Closed by: {reason})\n")
        f.write(f"Start: {arb_info['start'].isoformat()} | End: {arb_info['end'].isoformat()}\n")
        for leg in opp.legs:
            f.write(f"  [{leg.book_id}] {leg.selection}: {decimal_to_american(leg.odds_decimal)} (Stake: ${leg.stake:.2f})\n")
        f.write("="*80 + "\n\n")
    print(f"Arb Finished: {opp.margin:.2%} | {opp.away_team} @ {opp.home_team} | Duration: {duration:.1f}s")

def get_parser(sb):
    if sb == "betano": return BetanoParser()
    if sb == "betmgm": return BetMGMParser()
    if sb == "caesars": return CaesarsParser()
    if sb == "draftkings": return DraftKingsParser()
    if sb == "fanduel": return FanDuelParser()

import argparse

def main():
    parser = argparse.ArgumentParser(description="Replay a recorded sports betting timeline through the scanner.")
    default_timeline = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "data2", "timeline.jsonl")
    parser.add_argument("--timeline", type=str, default=default_timeline, help="Path to the timeline.jsonl file.")
    args = parser.parse_args()

    # Suppress normalization failed logs
    logging.getLogger("arbfinder.normalization.unresolved_log").setLevel(logging.ERROR)
    logging.getLogger("arbfinder.parsers.unresolved_log").setLevel(logging.ERROR)

    timeline_path = args.timeline
    if not os.path.exists(timeline_path):
        print(f"Timeline not found at {timeline_path}")
        return

    with open(timeline_path, "r") as f:
        timeline = [json.loads(line) for line in f]

    print(f"Loaded {len(timeline)} events from timeline.")

    normalizer = Normalizer({
        "DraftKings": DraftKingsNormalizer(),
        "FanDuel": FanDuelNormalizer(),
        "BetMGM": BetMGMNormalizer(),
        "Betano": BetanoNormalizer(),
        "Caesars": CaesarsNormalizer(),
    })

    store = BucketStore()
    resolver = TimeResolver()
    matcher = Matcher(store, resolver)

    grouper = MarketGrouper()
    thresholds = ScannerThresholds(min_margin=0.01, max_odds_age_seconds=60.0) # 60s for realistic test
    staleness = StalenessFilter(max_age_seconds=60.0) 
    dedup = DedupTracker(cooldown_seconds=0.0) # Set to 0 so we get continuous Opportunity objects while arb is active
    
    output_file = os.path.join(os.path.dirname(__file__), "arbs_output.txt")
    with open(output_file, "w") as f:
        f.write("Arbitrage Opportunities (with durations):\n")
        
    expected = {
        "moneyline": {"away", "home"},
        "run_line": {"away", "home"},
        "total": {"over", "under"},
        "spread": {"away", "home"},
        "two-way-handicap": {"away", "home"}
    }
    
    scanner = Scanner(grouper, thresholds, staleness, dedup, [], expected, lambda _: 100.0)

    parsers = {
        "betano": get_parser("betano"),
        "betmgm": get_parser("betmgm"),
        "caesars": get_parser("caesars"),
        "draftkings": get_parser("draftkings"),
        "fanduel": get_parser("fanduel")
    }

    updates_processed = 0
    active_arbs = {} # MarketGroupKey -> {"start": datetime, "last": datetime, "opp": Opportunity}
    total_arbs_found = 0

    for idx, event in enumerate(timeline):
        simulated_now = datetime.fromtimestamp(event["timestamp"], timezone.utc)
        sb = event["sportsbook"]
        ftype = event["file_type"]
        msg_dir_name = "messages" if sb == "caesars" else f"{sb}_messages"
        if event.get("path"):
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            fpath = os.path.join(project_root, event["path"])
        else:
            fpath = os.path.join(os.path.dirname(timeline_path), sb, msg_dir_name, event["file_name"])

        parser = parsers[sb]
        updates = []

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                is_json = event["file_type"] == "json"
                if sb == "fanduel" and event["file_type"] == "ws":
                    is_json = True
                    
                if is_json:
                    d = json.load(f)
                    payload = d.get("data", d)
                    url = d.get("_DEBUG_URL", "")
                    
                    if not url:
                        # Fallback for fixture loading
                        if sb == "draftkings": url = "api/sportscontent/v1/markets"
                        elif sb == "fanduel": url = "content-managed-page"
                        elif sb == "betmgm": url = "fixture-view"
                        elif sb == "betano": url = "https://www.betano.ca/danae-webapi/api/live/overview/1"
                        elif sb == "caesars": url = "https://api.americanwagering.com/v4/home"
                        
                        if sb == "fanduel" and "ws" in event["file_name"]:
                            url = "https://smp.on.sportsbook.fanduel.ca/api/sports/fixedodds/readonly/v1/getMarketPrices?priceHistory=1"
                    
                    updates = parser.handle_http_body(url, json.dumps(payload) if not isinstance(payload, str) else payload)
                else:
                    content = f.read().strip()
                    if sb in ["betano", "betmgm"]:
                        content += "\x1e"
                    updates = parser.handle_ws_frame(content)
        except Exception as e:
            print(f"Error parsing {fpath}: {e}")
            continue

        if not updates:
            continue
            
        # Overwrite the 'captured_at' timestamp with our simulated replay time
        updates = [dataclasses.replace(u, captured_at=simulated_now) for u in updates]

        normalized = normalizer.normalize_batch(updates)
        updates_processed += len(normalized)

        for u in normalized:
            bucket = matcher.assign(u)
            ms = MatchOutputBuilder.from_bucket(bucket)
            group_key = grouper.add(ms)
            
            opp = scanner.process(ms, now=simulated_now)
            
            if opp is not None:
                if group_key not in active_arbs:
                    active_arbs[group_key] = {
                        "start": simulated_now,
                        "last": simulated_now,
                        "opp": opp
                    }
                else:
                    active_arbs[group_key]["last"] = simulated_now
                    # Keep the best margin seen
                    if opp.margin > active_arbs[group_key]["opp"].margin:
                        active_arbs[group_key]["opp"] = opp
            else:
                if group_key in active_arbs:
                    arb_info = active_arbs.pop(group_key)
                    arb_info["end"] = simulated_now
                    duration = (simulated_now - arb_info["start"]).total_seconds()
                    write_arb_summary(output_file, arb_info, duration, "Line moved or book stale")
                    total_arbs_found += 1
                    
        # Purge stale arbs periodically
        if idx % 50 == 0:
            stale_keys = []
            for k, arb_info in active_arbs.items():
                if (simulated_now - arb_info["last"]).total_seconds() > thresholds.max_odds_age_seconds:
                    stale_keys.append(k)
            for k in stale_keys:
                arb_info = active_arbs.pop(k)
                arb_info["end"] = arb_info["last"] + timedelta(seconds=thresholds.max_odds_age_seconds)
                duration = (arb_info["end"] - arb_info["start"]).total_seconds()
                write_arb_summary(output_file, arb_info, duration, "Timeout")
                total_arbs_found += 1
            
        if idx % 100 == 0:
            print(f"Processed {idx}/{len(timeline)} events. Found {total_arbs_found} closed arbs so far...")

    # Flush remaining active arbs at end of replay
    for k, arb_info in active_arbs.items():
        arb_info["end"] = simulated_now
        duration = (simulated_now - arb_info["start"]).total_seconds()
        write_arb_summary(output_file, arb_info, duration, "End of timeline")
        total_arbs_found += 1

    print(f"Replay complete! Processed {updates_processed} normalized updates. Found {total_arbs_found} total arbs.")

if __name__ == "__main__":
    main()
