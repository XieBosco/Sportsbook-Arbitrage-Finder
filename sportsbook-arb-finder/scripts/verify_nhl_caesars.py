"""Script to run CaesarsDebugParser through nhl_data dataset line by line and verify every input and output."""

import json
import logging
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from arbfinder.parsers.caesars_debug import CaesarsDebugParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_caesars")


def main():
    timeline_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "nhl_data", "timeline.jsonl"))
    messages_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "nhl_data", "caesars", "messages"))

    if not os.path.exists(timeline_path):
        logger.error("Timeline not found: %s", timeline_path)
        sys.exit(1)

    with open(timeline_path, "r", encoding="utf-8") as fp:
        timeline = [json.loads(line) for line in fp if line.strip()]

    caesars_entries = [e for e in timeline if e.get("sportsbook") == "caesars"]
    logger.info("Total timeline entries: %d | Caesars entries: %d", len(timeline), len(caesars_entries))

    parser = CaesarsDebugParser()

    total_inputs = len(caesars_entries)
    anomalies = []

    for idx, event in enumerate(caesars_entries, 1):
        file_name = event["file_name"]
        file_type = event["file_type"]
        fpath = os.path.join(messages_dir, file_name)

        if not os.path.exists(fpath):
            err = f"[{idx}/{total_inputs}] File not found: {fpath}"
            logger.error(err)
            anomalies.append(err)
            continue

        if file_type == "json":
            with open(fpath, "r", encoding="utf-8") as f:
                body = f.read()
            try:
                json_data = json.loads(body)
            except Exception as exc:
                err = f"[{idx}/{total_inputs}] {file_name}: JSON parse failure: {exc}"
                logger.error(err)
                anomalies.append(err)
                continue

            url = json_data.get("_DEBUG_URL", "")
            is_relevant = parser.relevant_http_url(url)

            if is_relevant:
                before_ev = len(parser.reference_data["events"])
                before_mkt = len(parser.reference_data["markets"])
                before_sel = len(parser.reference_data["selections"])

                updates = parser.handle_http_body(url, body)
                if updates != []:
                    err = f"[{idx}/{total_inputs}] JSON HTTP body returned non-empty updates: {updates}"
                    logger.error(err)
                    anomalies.append(err)

                after_ev = len(parser.reference_data["events"])
                after_mkt = len(parser.reference_data["markets"])
                after_sel = len(parser.reference_data["selections"])

                # Check if reference data was registered
                if after_ev == before_ev and after_mkt == before_mkt and after_sel == before_sel:
                    err = f"[{idx}/{total_inputs}] Relevant HTTP {url} ({file_name}) registered 0 entities"
                    logger.error(err)
                    anomalies.append(err)
                else:
                    logger.info(
                        "[%d/%d] Relevant HTTP %s: +%d ev, +%d mkt, +%d sel (total ev=%d, mkt=%d, sel=%d)",
                        idx,
                        total_inputs,
                        file_name,
                        after_ev - before_ev,
                        after_mkt - before_mkt,
                        after_sel - before_sel,
                        after_ev,
                        after_mkt,
                        after_sel,
                    )
            else:
                # Non-relevant HTTP URLs (e.g. navigation, banners) should return [] safely
                updates = parser.handle_http_body(url, body)
                if updates != []:
                    err = f"[{idx}/{total_inputs}] Non-relevant HTTP body returned updates: {updates}"
                    logger.error(err)
                    anomalies.append(err)
        else:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().strip()

            updates = parser.handle_ws_frame(content)

            # Verification of output
            for u in updates:
                # 1. Book ID
                if u.book_id != "Caesars":
                    err = f"[{idx}/{total_inputs}] {file_name}: Wrong book_id: {u.book_id}"
                    logger.error(err)
                    anomalies.append(err)

                # 2. Team names: MUST NOT BE EMPTY
                if not u.raw_home_team or not u.raw_away_team:
                    err = f"[{idx}/{total_inputs}] {file_name}: Empty team names: home='{u.raw_home_team}', away='{u.raw_away_team}' (event_id='{u.raw_event_id}')"
                    logger.error(err)
                    anomalies.append(err)

                # 3. Event ID
                if not u.raw_event_id:
                    err = f"[{idx}/{total_inputs}] {file_name}: Empty raw_event_id for sel={u.raw_selection_id}"
                    logger.error(err)
                    anomalies.append(err)

                # 4. Odds value
                if u.odds_value is None or u.odds_value <= 1.0:
                    err = f"[{idx}/{total_inputs}] {file_name}: Invalid odds_value: {u.odds_value}"
                    logger.error(err)
                    anomalies.append(err)

                # 5. Selection name
                if not u.raw_selection:
                    err = f"[{idx}/{total_inputs}] {file_name}: Empty raw_selection"
                    logger.error(err)
                    anomalies.append(err)

    logger.info("=" * 60)
    logger.info("VERIFICATION COMPLETE ACROSS ALL %d ENTRIES", total_inputs)
    logger.info("Stats: %s", json.dumps({k: v for k, v in parser.stats.items() if k != "errors"}, indent=2))
    logger.info("Total parser errors logged: %d", len(parser.stats["errors"]))
    logger.info("Total anomalies detected: %d", len(anomalies))

    if parser.stats["errors"]:
        logger.error("Sample parser errors:")
        for e in parser.stats["errors"][:20]:
            logger.error("  %s", e)

    if anomalies:
        logger.error("Sample anomalies:")
        for a in anomalies[:20]:
            logger.error("  %s", a)
    else:
        logger.info("SUCCESS: 0 anomalies across all %d inputs!", total_inputs)


if __name__ == "__main__":
    main()
