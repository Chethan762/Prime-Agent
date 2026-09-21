
from browser import open_page
p,b,page=open_page('https://example.com')
print('Title:', page.title())
b.close()
p.stop()
