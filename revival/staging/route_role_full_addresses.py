"""Surgical replacement of only the already-owned current-map routing sites."""
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'game_runtime.py'
data=path.read_bytes();newline='\r\n' if b'\r\n' in data else '\n'
text=data.decode('utf-8').replace('\r\n','\n')
replacements={
    'self.rt.map(self.position.value[0])':'self.rt.map(self.map_address)',
    'self.rt.map(receipt.location.address.map_id)':'self.rt.map(receipt.location.address)',
    'self.rt.map(offer.source.address.map_id)':'self.rt.map(offer.source.address)',
    'self.rt.map(location.address.map_id)':'self.rt.map(location.address)',
}
counts={before:text.count(before) for before in replacements}
if counts!={list(replacements)[0]:15,list(replacements)[1]:1,list(replacements)[2]:1,list(replacements)[3]:2}:
    raise ValueError('Current-map route sites changed: '+repr(counts))
for before,after in replacements.items():text=text.replace(before,after)
path.write_bytes(text.replace('\n',newline).encode('utf-8'))
print(counts)
