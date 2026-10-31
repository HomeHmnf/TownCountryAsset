from tools.database.country_data_import import _attribute_value


def test_attribute_value_preserves_types():
    assert _attribute_value(None, 'x') == (None, 'null')
    assert _attribute_value(True, 'x') == ('true', 'boolean')
    assert _attribute_value(3, 'x') == ('3', 'integer')
    assert _attribute_value(1.5, 'x') == ('1.5', 'real')
    assert _attribute_value('v', 'x') == ('v', 'text')
