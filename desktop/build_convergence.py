"""Re-render the released audit figure from its bundled numerical metrics."""
from pathlib import Path
import json

def main():
 import matplotlib
 matplotlib.use('Agg')
 from matplotlib.figure import Figure
 from matplotlib.backends.backend_agg import FigureCanvasAgg
 from ui_theme import style_figure
 root=Path(__file__).resolve().parent
 record=json.loads((root/'model_assets/metrics.json').read_text())
 for theme in ['light','dark']:
  folder=root/('model_assets' if theme=='light' else 'model_assets_dark');folder.mkdir(exist_ok=True)
  fig=Figure(figsize=(10,4.5));FigureCanvasAgg(fig);ax=fig.subplots();v=record['displacement_convergence']
  ax.loglog([a['max_phase_rad'] for a in v],[a['max_ifg_error_over_peak'] for a in v],'o-')
  ax.axvline(.25,color='#a45332',ls='--',label='Caution threshold; not accuracy guarantee')
  ax.set(xlabel='Maximum physical displacement phase (rad)',ylabel='Maximum IFG error / ideal IFG peak',title='Expansion compared with exact OPD-dependent cosine sum');ax.grid(alpha=.2,which='both');ax.legend();fig.tight_layout()
  if theme=='dark':style_figure(fig,'dark')
  fig.savefig(folder/'convergence.png',dpi=160,facecolor=fig.get_facecolor())

if __name__=='__main__':main()
