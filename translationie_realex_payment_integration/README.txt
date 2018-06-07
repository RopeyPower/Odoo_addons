This addon only works on HTTPS, so it requires a reverse proxy set up for odoo.

Requires wand and imagemagick to create the png receipts
Installation guide for wand here:
http://docs.wand-py.org/en/latest/guide/install.html#install-imagemagick-on-windows

wand and svgwrite need folders need to copied from "Odoo 9.0-20160510\server\openerp\addons\translationie_realex_payment_integration\external dependencies"
into "Odoo 9.0-20160510\server"

Requires that the web.base.url system parameter be set correctly. Can be found under Settings - Technical - System Parameters
Also requires the system parameter "web.base.url.freeze" with value True to be added.

Needs the which.py file at C:\Program Files (x86)\Odoo 9.0-20160510\server\openerp\tools
to be modified in the which_files() method from:

	elif isinstance(path, str):

to:
	elif isinstance(path, str) or isinstance(path, unicode):

because wand addon seems to change the path variable from string to uinicode when it adds itself to the path when called by odoo.