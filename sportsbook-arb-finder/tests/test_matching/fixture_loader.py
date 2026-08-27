import glob
import json
import os

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

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")

def get_all_normalized_updates():
    normalizer = Normalizer(
        normalizers={
            "DraftKings": DraftKingsNormalizer(),
            "FanDuel": FanDuelNormalizer(),
            "BetMGM": BetMGMNormalizer(),
            "Betano": BetanoNormalizer(),
            "Caesars": CaesarsNormalizer(),
        }
    )

    all_normalized_updates = []

    # DraftKings
    parser = DraftKingsParser()
    ref_path = os.path.join(FIXTURES_DIR, "draftkings", "draftkings_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("api/sportscontent/v1/markets", json.dumps(d.get("data", d)))
    updates = []
    for mf in sorted(glob.glob(os.path.join(FIXTURES_DIR, "draftkings", "draftkings_messages", "ws_*.txt"))):
        with open(mf, "r", encoding="utf-8") as f:
            updates.extend(parser.handle_ws_frame(f.read().strip()))
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    # FanDuel
    parser = FanDuelParser()
    ref_path = os.path.join(FIXTURES_DIR, "fanduel", "fanduel_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("content-managed-page", json.dumps(d.get("data", d)))
    updates = []
    for mf in sorted(glob.glob(os.path.join(FIXTURES_DIR, "fanduel", "fanduel_messages", "ws_*.txt"))):
        with open(mf, "r", encoding="utf-8") as f:
            d = json.load(f)
            msg_body = json.dumps(d.get("data", d))
        updates.extend(parser.handle_http_body("https://smp.on.sportsbook.fanduel.ca/api/sports/fixedodds/readonly/v1/getMarketPrices?priceHistory=1", msg_body))
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    # BetMGM
    parser = BetMGMParser()
    ref_path = os.path.join(FIXTURES_DIR, "betmgm", "betmgm_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("fixture-view", json.dumps(d.get("data", d)))
    updates = []
    for mf in sorted(glob.glob(os.path.join(FIXTURES_DIR, "betmgm", "betmgm_messages", "ws_*.txt"))):
        with open(mf, "r", encoding="utf-8") as f:
            updates.extend(parser.handle_ws_frame(f.read().strip() + "\x1e"))
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    # Betano
    parser = BetanoParser()
    ref_path = os.path.join(FIXTURES_DIR, "betano", "betano_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("https://www.betano.ca/danae-webapi/api/live/overview/1", json.dumps(d.get("data", d)))
    updates = []
    for mf in sorted(glob.glob(os.path.join(FIXTURES_DIR, "betano", "betano_messages", "ws_*.txt"))):
        with open(mf, "r", encoding="utf-8") as f:
            updates.extend(parser.handle_ws_frame(f.read().strip() + "\x1e"))
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    # Caesars
    parser = CaesarsParser()
    ref_path = os.path.join(FIXTURES_DIR, "caesars", "messages", "json_5.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        parser.handle_http_body("https://api.americanwagering.com/v4/home", f.read())
    updates = []
    for mf in sorted(glob.glob(os.path.join(FIXTURES_DIR, "caesars", "messages", "ws_*.txt"))):
        with open(mf, "r", encoding="utf-8") as f:
            updates.extend(parser.handle_ws_frame(f.read().strip()))
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    return all_normalized_updates
