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


def test_github_reading_copy_is_current_and_preserves_all_scientific_text():
    root=Path(theory.__file__).parent
    rendered=theory.build_github_markdown(root)
    assert (root/'THEORY_GITHUB.md').read_text(encoding='utf-8')==rendered
    assert '```math' not in rendered and '[[equation:' not in rendered
    numbers=[]
    def restore(match):
        number=int(match[1]);numbers.append(number)
        return '[[equation:'+theory.NUMBERING[number-1]+']]'
    restored=re.sub(r'<p align="center">\n<picture>.*?</picture>\n\((\d+)\)\n</p>',
                    restore,rendered,flags=re.S)
    restored=re.sub(r'\n<!-- Generated[^\n]*\nThis reading copy[^\n]*\n','',restored,count=1)
    source=(root/'THEORY.md').read_text(encoding='utf-8')
    assert restored==theory.prepare_equation_blocks(source)
    assert numbers==list(range(1,16))


def test_github_equation_images_exist_in_both_themes_with_accessible_labels():
    from html.parser import HTMLParser
    root=Path(theory.__file__).parent
    class Images(HTMLParser):
        def __init__(self):
            super().__init__();self.images=[];self.sources=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='img':self.images.append(attrs)
            if tag=='source':self.sources.append(attrs)
    parser=Images();parser.feed(theory.build_github_markdown(root))
    assert len(parser.images)==len(parser.sources)==15
    for number,(image,source) in enumerate(zip(parser.images,parser.sources),1):
        assert (root/image['src']).is_file()
        assert (root/source['srcset']).is_file()
        assert source['media']=='(prefers-color-scheme: dark)'
        assert image['alt'].startswith(f'Equation ({number}): ')
        assert int(image['width'])>0


def test_github_reader_rejects_stale_equation_assets(monkeypatch):
    root=Path(theory.__file__).parent
    original=theory.ensure_assets
    def stale_assets(root,theme):
        assets=original(root,theme)
        assets['chemical']['latex']='$wrong$'
        return assets
    monkeypatch.setattr(theory,'ensure_assets',stale_assets)
    with pytest.raises(ValueError,match='asset differs from canonical equation'):
        theory.build_github_markdown(root)
