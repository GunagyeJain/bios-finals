from egovision.io.frames import factory_of


def test_factory_of_strips_clip_number():
    assert factory_of("MTL-SGF00106-021") == "MTL-SGF00106"
    assert factory_of("mytronlabs-000003-002") == "mytronlabs-000003"
    assert factory_of("fixture_001") == "fixture"
