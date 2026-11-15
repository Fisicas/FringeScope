"""GitHub-native equations must agree with the offline and web renderers."""
from pathlib import Path
import re
import pytest
import build_theory as theory


def test_public_theory_has_complete_numbered_math_instead_of_placeholders():
    source=(Path(theory.__file__).parent/'THEORY.md').read_text(encoding='utf-8')
    assert '[[equation:' not in source
    assert len(re.findall(r'^```math$',source,re.M))==15
    prepared=theory.prepare_equation_blocks(source)
    assert '```math' not in prepared
    keys=re.findall(r'\[\[equation:([a-z_]+)\]\]',prepared)
    assert set(keys)==set(theory.EQUATIONS) and len(keys)==15


def test_theory_rejects_mismatch_between_published_math_and_bundled_equations():
    with pytest.raises(ValueError,match='canonical numbered equation'):
        theory.prepare_equation_blocks('```math\nx=wrong\n```')
