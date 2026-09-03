"""Tests for pipeline configuration loading and validation."""

import pytest

from arbfinder.pipeline.config import AppConfig, load_config


class TestLoadConfig:
    """Verify config loading from YAML with pydantic validation."""

    def test_valid_config_loads(self, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            """
cdp_port: 19222
books:
  - name: TestBook
    url_pattern: "testbook.com"
    parser_class: "arbfinder.parsers.draftkings.DraftKingsParser"
    normalizer_class: "arbfinder.normalization.book_normalizers.draftkings_normalizer.DraftKingsNormalizer"

scanner:
  min_margin: 0.01
  max_odds_age_seconds: 5.0
  min_legs_required: 2
  excluded_book_pairs: []
""",
            encoding="utf-8",
        )
        config = load_config(config_file)
        assert len(config.books) == 1
        assert config.books[0].name == "TestBook"
        assert config.cdp_port == 19222

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/settings.yaml")

    def test_missing_books_field_raises(self, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("cdp_port: 19222\n", encoding="utf-8")
        with pytest.raises(Exception):  # pydantic ValidationError
            load_config(config_file)

    def test_empty_file_raises(self, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            load_config(config_file)

    def test_invalid_book_config_raises(self, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            """
books:
  - name: TestBook
""",
            encoding="utf-8",
        )
        with pytest.raises(Exception):  # Missing url_pattern, parser_class, etc.
            load_config(config_file)

    def test_defaults_applied(self, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            """
books:
  - name: TestBook
    url_pattern: "testbook.com"
    parser_class: "some.module.Parser"
    normalizer_class: "some.module.Normalizer"
""",
            encoding="utf-8",
        )
        config = load_config(config_file)
        assert config.cdp_port == 19222
        assert config.sinks.console_enabled is True
        assert config.sinks.execution_enabled is False
        assert config.server.port == 8000
        assert config.books[0].enabled is True

    def test_book_disabled(self, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            """
books:
  - name: TestBook
    enabled: false
    url_pattern: "testbook.com"
    parser_class: "some.module.Parser"
    normalizer_class: "some.module.Normalizer"
""",
            encoding="utf-8",
        )
        config = load_config(config_file)
        assert config.books[0].enabled is False

    def test_multiple_books(self, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            """
books:
  - name: BookA
    url_pattern: "booka.com"
    parser_class: "mod.ParserA"
    normalizer_class: "mod.NormA"
  - name: BookB
    url_pattern: "bookb.com"
    parser_class: "mod.ParserB"
    normalizer_class: "mod.NormB"
""",
            encoding="utf-8",
        )
        config = load_config(config_file)
        assert len(config.books) == 2
        assert config.books[0].name == "BookA"
        assert config.books[1].name == "BookB"

    def test_scanner_thresholds_from_yaml(self, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            """
books:
  - name: TestBook
    url_pattern: "test.com"
    parser_class: "m.P"
    normalizer_class: "m.N"
scanner:
  min_margin: 0.05
  max_odds_age_seconds: 10.0
""",
            encoding="utf-8",
        )
        config = load_config(config_file)
        assert config.scanner.min_margin == 0.05
        assert config.scanner.max_odds_age_seconds == 10.0
