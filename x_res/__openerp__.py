# -*- coding: utf-8 -*-
{
    'name': "x_res",

    'summary': """
        Custom modifications adding new resource models for translation.ie""",

    'description': """
        Adds the models x_res.languages, x_res.languages.pairs and x_res.cat for recording translator languages and cat tools respectively.
    """,

    'author': "Translation.ie",
    'website': "http://www.translation.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
		'security/ir.model.access.csv',
		'x_res_languages_view.xml',
		'x_res_cat_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}