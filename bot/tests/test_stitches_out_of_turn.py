from bot.main import should_warn_stitches_out_of_turn


def _photos():
    return [{"type": "photo", "photo": {"owner_id": 1, "id": 10}}]


def test_warns_when_stitches_in_pre_mode():
    assert should_warn_stitches_out_of_turn("grow_step_2", "вышито 1500", []) is True


def test_warns_when_stitches_keyword_variant():
    assert should_warn_stitches_out_of_turn("epic_care_1", "стежки готовы", []) is True


def test_warns_when_photo_only_in_pre_mode():
    assert should_warn_stitches_out_of_turn("grow_step_2", "", _photos()) is True


def test_does_not_warn_when_actually_waiting_norm():
    assert should_warn_stitches_out_of_turn("grow_step_2_norm", "вышито 1500", _photos()) is False


def test_does_not_warn_when_actually_waiting_x2():
    assert should_warn_stitches_out_of_turn("grow_step_2_x2", "вышито 3000", _photos()) is False


def test_does_not_warn_when_epic_egg_waiting():
    assert should_warn_stitches_out_of_turn("epic_egg_1_norm", "вышито 1000", _photos()) is False


def test_does_not_warn_when_epic_care_waiting():
    assert should_warn_stitches_out_of_turn("epic_care_1_norm", "вышито 1000", _photos()) is False


def test_does_not_warn_when_legend_waiting():
    assert should_warn_stitches_out_of_turn("legend_1_norm", "вышито 1000", _photos()) is False


def test_does_not_warn_for_pure_number_in_garden():
    assert should_warn_stitches_out_of_turn("await_garden", "2", []) is False


def test_does_not_warn_for_idle_text():
    assert should_warn_stitches_out_of_turn("idle", "привет", []) is False


def test_does_not_warn_for_idle_photo():
    assert should_warn_stitches_out_of_turn("idle", "", _photos()) is False


def test_does_not_warn_for_unrelated_text_in_grow():
    assert should_warn_stitches_out_of_turn("grow_step_2", "что делать дальше?", []) is False
