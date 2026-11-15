"""Readable display values; never used to round model inputs or exported data."""
import math
from matplotlib.ticker import ScalarFormatter


def number(value,scientific=True):
    value=float(value)
    if not math.isfinite(value):return str(value)
    if value==0:return '0'
    if scientific and (abs(value)<.01 or abs(value)>=1e5):
        mantissa,exponent=f'{value:.2e}'.split('e')
        return mantissa.rstrip('0').rstrip('.')+'e'+str(int(exponent))
    result=f'{value:.2f}'.rstrip('0').rstrip('.')
    return '0' if result=='-0' else result


class ReadableScalarFormatter(ScalarFormatter):
    """At most two decimals in tick mantissas, with a typeset scale exponent."""
    def __init__(self):
        super().__init__(useOffset=True,useMathText=True)
        self.set_powerlimits((-2,4))
    def __call__(self,value,pos=None):
        if len(self.locs)==0:return ''
        scaled=(value-self.offset)/(10.**self.orderOfMagnitude)
        label=self.fix_minus(number(scaled,scientific=False))
        return r'$\mathdefault{'+label+'}$'
