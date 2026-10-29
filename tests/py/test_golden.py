from studykit import golden, pandoc, tools


def test_display_block_with_leading_equals_is_detected():
    markdown = "$$\na\n=\nb\n$$\n"
    formulas = [golden.Formula(t, d) for t, d in pandoc.math_nodes(markdown)]
    assert golden.unparsed_display_blocks(markdown, formulas) == 1


def test_well_formed_display_block_is_math():
    markdown = "$$\na =\nb\n$$\n"
    formulas = [golden.Formula(t, d) for t, d in pandoc.math_nodes(markdown)]
    assert golden.unparsed_display_blocks(markdown, formulas) == 0


def test_typst_check_reports_unconvertible_math():
    root = tools.repo_root()
    assert golden.typst_check(root, "$$\n\\frac{a}{b}\n$$\n") is None
    assert "Could not convert" in golden.typst_check(root, "$$\n\\ce{H2O}\n$$\n")


def test_katex_check_is_strict():
    root = tools.repo_root()
    ok, umlaut = golden.katex_check(
        root, [golden.Formula(r"\frac{a}{b}", True), golden.Formula("ä", False)]
    )
    assert ok is None
    assert umlaut is not None
