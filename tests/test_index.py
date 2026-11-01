import sqlite3
from contextlib import closing

import pytest

from egovision import config


@pytest.fixture
def outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    monkeypatch.setattr(config, "INDEX_DB", tmp_path / "outputs" / "index.db")
    from egovision.fixtures import make
    make("fixture_001", seconds=3)
    (config.OUTPUTS / "references").mkdir()                    # never indexed as a clip
    return config.OUTPUTS


def _q(sql):
    with closing(sqlite3.connect(config.INDEX_DB)) as db:
        return db.execute(sql).fetchall()


def test_build_indexes_every_file_of_the_fixture(outputs):
    from egovision.index.build import build
    build()
    assert _q("SELECT clip, factory, n_frames FROM clips") == [("fixture_001", "fixture", 90)]
    assert _q("SELECT COUNT(*) FROM segments") == [(3,)]
    assert _q("SELECT COUNT(*) FROM frame_summary") == [(90,)]
    assert _q("SELECT COUNT(*) FROM contacts") == [(3,)]
    assert _q("SELECT COUNT(*) FROM steps") == [(5,)]
    assert _q("SELECT kind FROM alerts ORDER BY kind") == [("safety",), ("step_missing",)]
    assert ("ours.lr_accuracy", 0.97) in _q("SELECT key, value FROM metrics")
    green, yellow, red = _q("SELECT green_share, yellow_share, red_share FROM clips")[0]
    assert (green, yellow, red) == pytest.approx((2 / 3, 1 / 3, 0.0))
    assert _q("SELECT typeof(t_start) FROM contacts LIMIT 1") == [("real",)]


def test_rebuild_keeps_registered_products(outputs):
    from egovision.index.build import build, register_product
    build()
    register_product("dataset", "demo_v1", "exports/demo_v1", {"light": "green"}, 4)
    build()
    assert _q("SELECT kind, name, filter_json, n_items FROM products") == [
        ("dataset", "demo_v1", '{"light": "green"}', 4)]


def test_register_product_works_before_any_build(outputs):
    from egovision.index.build import register_product
    register_product("module", "m1", "exports/m1", {}, 1)
    assert _q("SELECT name FROM products") == [("m1",)]


def test_fixtures_stay_out_when_real_clips_exist(outputs):
    import shutil
    from egovision.index import query
    from egovision.index.build import build
    real = config.OUTPUTS / "REAL-0001-001"
    shutil.copytree(config.OUTPUTS / "fixture_001", real)
    for f in real.iterdir():                     # outputs carry their clip name inside; relabel the copy
        if f.suffix in (".json", ".csv", ".jsonl"):
            f.write_text(f.read_text(encoding="utf-8").replace("fixture_001", real.name), encoding="utf-8")
    build()
    assert query.library()["clip"].tolist() == [real.name]


def test_registering_a_dataset_again_replaces_it(outputs):
    from egovision.index.build import register_product
    register_product("dataset", "demo", outputs, {}, 2)
    register_product("dataset", "demo", outputs, {}, 85)
    assert _q("SELECT name, n_items FROM products WHERE kind = 'dataset'") == [("demo", 85)]
