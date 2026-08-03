from bot.main import is_int_str


def test_plain_digit():
    assert is_int_str("2") is True


def test_multi_digit():
    assert is_int_str("12") is True


def test_zero():
    assert is_int_str("0") is True


def test_superscript_two():
    """Регрессия бага ValueError: invalid literal for int() with base 10: '²'.
    Юзер ввёл надстрочную двойку (U+00B2). str.isdigit() возвращает True,
    но int() падает. is_int_str должен вернуть False."""
    assert is_int_str("²") is False


def test_superscript_three():
    assert is_int_str("³") is False


def test_roman_numeral():
    assert is_int_str("Ⅷ") is False


def test_arabic_indic_digit():
    assert is_int_str("٢") is False


def test_letter():
    assert is_int_str("a") is False


def test_word():
    assert is_int_str("два") is False


def test_empty():
    assert is_int_str("") is False


def test_negative():
    assert is_int_str("-1") is False


def test_float():
    assert is_int_str("1.5") is False


def test_space_padded_handled_by_caller():
    assert is_int_str(" 2 ") is False
