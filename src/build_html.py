"""Inject data/data.json and src/logo.png into src/template.html -> index.html."""
import base64, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
t = (root / 'src/template.html').read_text()
logo = 'data:image/png;base64,' + base64.b64encode((root / 'src/logo.png').read_bytes()).decode()
(root / 'index.html').write_text(t.replace('__LOGO__', logo).replace('__DATA__', (root / 'data/data.json').read_text()))
print('wrote index.html')
